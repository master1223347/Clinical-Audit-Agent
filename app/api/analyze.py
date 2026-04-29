"""§11.1 — POST /analyze and GET /analyze/cached/{transcript_id}."""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

import app.core.extraction as _extraction_mod
from app.api.schemas import AnalyzeRequest
from app.core.dedup import dedup_claims
from app.core.safety import screen_output
from app.models.analyze import AnalyzeResponse, RedFlagOnlySpan
from app.models.claim import ClinicalClaim, Evidence
from app.models.context import TrackingContext
from app.models.enums import (
    DoctorEditOrigin,
    DoctorReviewStatus,
    EventType,
    ExtractionType,
    InputType,
    RiskLevel,
    SafetyStatus,
)
from app.models.input import PatientInput
from app.rules.red_flag_rules import is_urgent_match, match_red_flags
from app.rules.risk_messages import PATIENT_MESSAGES
from app.storage.deps import get_repo
from app.storage.repository import ClaimsRepository

router = APIRouter(tags=["analyze"])

_log = logging.getLogger(__name__)


def _run_pipeline(
    *,
    input_id: str,
    patient_id: str,
    raw_text: str,
    input_type: str = "text",
    context: TrackingContext | None = None,
    repo: ClaimsRepository,
) -> AnalyzeResponse:
    """Core pipeline: extract → dedup → safety → red-flags → persist."""
    prompt_hash = _extraction_mod.PROMPT_VERSION_HASH
    model_id = _extraction_mod.MODEL_ID
    now = datetime.now(tz=timezone.utc)

    # Check cache before constructing PatientInput (avoid allocation on hit)
    existing = repo.get_analyze_response(input_id, prompt_hash, model_id)
    if existing is not None:
        claims_rows = repo.list_claims_for_response(input_id, prompt_hash, model_id)
        claims = _rows_to_claims(claims_rows)
        return AnalyzeResponse(
            inputId=input_id,
            promptVersionHash=prompt_hash,
            modelId=model_id,
            claims=claims,
            escalationMessage=existing.get("escalation_message"),
            redFlagOnlySpans=_parse_red_flag_spans(existing.get("red_flag_only_spans_json")),
            createdAt=datetime.fromisoformat(existing["created_at"]),
        )

    patient_input = PatientInput(
        inputId=input_id,
        patientId=patient_id,
        inputType=input_type,
        rawText=raw_text,
        source="patientApp",
        createdAt=now,
    )

    # Extract claims via LLM
    raw_claims = _extraction_mod.extract_claims_from_text(
        raw_text=raw_text,
        patient_id=patient_id,
        input_id=input_id,
        context=context,
    )

    # Dedup before safety screen (§2)
    deduped = dedup_claims(raw_claims)

    # Safety screen each claim
    surfaced_claims = []
    for claim in deduped:
        block = screen_output(patient_input, claim.claimText)
        if block is None:
            surfaced_claims.append(claim)
        # Blocked claims are not persisted

    # Red-flag rules against raw_text
    rf_matches = match_red_flags(raw_text)

    # Escalation: urgent if any claim is urgent OR any urgent red-flag match
    urgent_claim_ids = {
        c.claimId for c in surfaced_claims if c.riskLevel == RiskLevel.URGENT
    }
    urgent_rf_keys = {rk for rk, _s, _e in rf_matches if is_urgent_match(rk)}

    is_urgent = bool(urgent_claim_ids or urgent_rf_keys)
    escalation_message: str | None = None
    if is_urgent:
        escalation_message = PATIENT_MESSAGES[RiskLevel.URGENT]

    # Red-flag-only spans: rule matches without a corresponding urgent claim evidence
    urgent_claim_evidences = {
        (c.evidence.startChar, c.evidence.endChar)
        for c in surfaced_claims
        if c.riskLevel == RiskLevel.URGENT
    }
    red_flag_only_spans: list[RedFlagOnlySpan] = []
    for rule_key, start, end in rf_matches:
        span_has_claim = any(
            abs(s - start) <= 5 for s, _e in urgent_claim_evidences
        )
        if not span_has_claim:
            red_flag_only_spans.append(
                RedFlagOnlySpan(startChar=start, endChar=end, ruleKey=rule_key)
            )

    spans_json = (
        json.dumps([s.model_dump() for s in red_flag_only_spans])
        if red_flag_only_spans
        else None
    )

    # Persist analyze_responses (always, even zero claims)
    repo.insert_analyze_response(
        input_id=input_id,
        prompt_version_hash=prompt_hash,
        model_id=model_id,
        patient_id=patient_id,
        raw_text=raw_text,
        escalation_message=escalation_message,
        red_flag_only_spans_json=spans_json,
        created_at=now.isoformat(),
    )

    # Persist claims
    for claim in surfaced_claims:
        repo.insert_claim_raw(
            claim_id=claim.claimId,
            input_id=input_id,
            prompt_version_hash=prompt_hash,
            model_id=model_id,
            patient_id=patient_id,
            claim_text=claim.claimText,
            original_claim_text=claim.originalClaimText,
            event_type=claim.eventType.value,
            evidence_text=claim.evidence.evidenceText,
            evidence_start=claim.evidence.startChar or 0,
            evidence_end=claim.evidence.endChar or 0,
            confidence=claim.confidence,
            extraction_type=claim.extractionType.value,
            risk_level=claim.riskLevel.value,
            safety_status=claim.safetyStatus.value,
            doctor_review_status=claim.doctorReviewStatus.value,
            doctor_edit_origin=claim.doctorEditOrigin.value if claim.doctorEditOrigin else None,
            created_at=claim.createdAt.isoformat(),
        )

    return AnalyzeResponse(
        inputId=input_id,
        promptVersionHash=prompt_hash,
        modelId=model_id,
        claims=surfaced_claims,
        escalationMessage=escalation_message,
        redFlagOnlySpans=red_flag_only_spans,
        createdAt=now,
    )


def _rows_to_claims(rows: list[dict]) -> list[ClinicalClaim]:
    """Reconstruct ClinicalClaim objects from DB rows."""
    claims = []
    for row in rows:
        claims.append(ClinicalClaim(
            claimId=row["claim_id"],
            patientId=row.get("patient_id", ""),
            inputId=row["input_id"],
            claimText=row["claim_text"],
            originalClaimText=row.get("original_claim_text"),
            eventType=EventType(row["event_type"]),
            confidence=row["confidence"],
            evidence=Evidence(
                evidenceText=row["evidence_text"],
                sourceType=InputType.TEXT,
                sourceId=row["input_id"],
                startChar=row["evidence_start"],
                endChar=row["evidence_end"],
            ),
            riskLevel=RiskLevel(row["risk_level"]),
            safetyStatus=SafetyStatus(row["safety_status"]),
            doctorReviewStatus=DoctorReviewStatus(row["doctor_review_status"]),
            doctorEditOrigin=(
                DoctorEditOrigin(row["doctor_edit_origin"])
                if row.get("doctor_edit_origin")
                else None
            ),
            extractionType=ExtractionType(row["extraction_type"]),
            createdAt=datetime.fromisoformat(row["created_at"]),
        ))
    return claims


def _parse_red_flag_spans(json_str: str | None) -> list[RedFlagOnlySpan]:
    if not json_str:
        return []
    try:
        items = json.loads(json_str)
        return [
            RedFlagOnlySpan.model_validate(item)
            for item in items
            if isinstance(item, dict)
        ]
    except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
        _log.error(
            "Failed to parse red_flag_only_spans_json: %s — value: %.200s",
            exc,
            json_str,
        )
        return []


@router.post("", response_model=AnalyzeResponse)
def analyze_input(req: AnalyzeRequest) -> AnalyzeResponse:
    """§11.1 — extract clinical claims from patient transcript."""
    repo = get_repo()
    input_id = str(uuid.uuid4())
    return _run_pipeline(
        input_id=input_id,
        patient_id=req.patientId,
        raw_text=req.rawText,
        input_type=req.inputType.value,
        context=req.context,
        repo=repo,
    )


@router.get("/cached/{transcript_id}", response_model=AnalyzeResponse)
def get_cached_analysis(transcript_id: str) -> AnalyzeResponse:
    """GET cached result by transcript_id (composite key with current hash+model).

    Returns 200 with claims=[] for zero-claim transcripts.
    Returns 404 only when never computed.
    """
    prompt_hash = _extraction_mod.PROMPT_VERSION_HASH
    model_id = _extraction_mod.MODEL_ID
    repo = get_repo()
    existing = repo.get_analyze_response(transcript_id, prompt_hash, model_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Not found — never computed")

    claims_rows = repo.list_claims_for_response(transcript_id, prompt_hash, model_id)
    claims = _rows_to_claims(claims_rows)
    return AnalyzeResponse(
        inputId=transcript_id,
        promptVersionHash=prompt_hash,
        modelId=model_id,
        claims=claims,
        escalationMessage=existing.get("escalation_message"),
        redFlagOnlySpans=_parse_red_flag_spans(existing.get("red_flag_only_spans_json")),
        createdAt=datetime.fromisoformat(existing["created_at"]),
    )
