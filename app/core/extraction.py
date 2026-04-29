"""§8.1 — Clinical Event Extraction via Anthropic Claude with prompt caching.

pilot.md C2/C3/H7: token counting via client.messages.count_tokens() only.
PROMPT_VERSION_HASH is sha256 of the cached system block, computed at module load.
MIN_CACHE_TOKENS_BY_MODEL threshold assertion runs at module import, before
FastAPI binds to a port.
"""

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone

import anthropic

from app.core.evidence import EvidenceNotFound, locate_evidence
from app.models.claim import ClinicalClaim, Evidence
from app.models.context import TrackingContext
from app.models.enums import (
    DoctorReviewStatus,
    EventType,
    ExtractionType,
    InputType,
    RiskLevel,
    SafetyStatus,
)

MODEL_ID: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

MIN_CACHE_TOKENS_BY_MODEL: dict[str, int] = {
    "claude-sonnet-4-6": 1024,
    "claude-opus-4-7": 1024,
    "claude-haiku-4-5": 2048,
}

_SYSTEM_PROMPT = """\
You are a clinical event extraction assistant for Dr Tracker, a health logging app.

Your task: analyse a patient health transcript and extract structured clinical claims.

Return ONLY a valid JSON array of claim objects. No other text, no markdown, no explanations.

## Output format — each claim object:

{
  "claimText": "Patient reported <symptom/event> ...",
  "eventType": "<one of the allowed event types>",
  "evidenceText": "<EXACT substring from the transcript that supports this claim>",
  "confidence": <0.0 to 1.0>,
  "extractionType": "<direct | interpretation>",
  "missingInfo": ["<field 1>", "<field 2>"],
  "riskLevel": "<low | medium | high | urgent | needs-review>",
  "safetyStatus": "<safe | medicationAdviceBlocked | diagnosisNotConfirmed | needsReview>",
  "eventTime": "<time reference from transcript, or null>"
}

## Allowed eventType values:
vomiting, nausea, stomachPain, feverPresent, feverAbsent, dizziness,
missedMedication, takenMedication, mealLogged, possibleFoodTrigger,
painIncrease, painDecrease, symptomImproved, symptomWorsened,
doctorInstruction, labReportUploaded, patientConcern, unknownHealthNote

## extractionType grading (Appendix A.1):
- direct: your claimText closely paraphrases the evidenceText — the claim is a
  near-paraphrase of what the patient actually said
- interpretation: you inferred beyond what the patient directly stated

## Rules:
1. Use "Patient reported..." language. NEVER diagnose.
2. evidenceText MUST be an exact verbatim substring of the transcript.
3. If a patient states a belief that sounds like self-diagnosis (e.g. "I think I have food
   poisoning"), use eventType="patientConcern" and safetyStatus="diagnosisNotConfirmed".
4. If the patient asks about or implies changing medication (stop/start/increase/decrease/taper),
   set safetyStatus="medicationAdviceBlocked" and do NOT recommend the change.
5. If confidence < 0.5 or the claim is purely interpretive, set riskLevel="needs-review".
6. Missing info: list what a doctor would want to know to interpret this event.

## Few-shot examples:

### Example 1 — direct extraction
Transcript: "Yesterday after dinner I threw up twice and felt dizzy."
Output:
[
  {
    "claimText": "Patient reported vomiting twice after dinner.",
    "eventType": "vomiting",
    "evidenceText": "threw up twice",
    "confidence": 0.95,
    "extractionType": "direct",
    "missingInfo": ["blood in vomit", "hydration status", "duration"],
    "riskLevel": "medium",
    "safetyStatus": "safe",
    "eventTime": "yesterday after dinner"
  },
  {
    "claimText": "Patient reported dizziness.",
    "eventType": "dizziness",
    "evidenceText": "felt dizzy",
    "confidence": 0.92,
    "extractionType": "direct",
    "missingInfo": ["severity", "duration", "associated symptoms"],
    "riskLevel": "low",
    "safetyStatus": "safe",
    "eventTime": "yesterday after dinner"
  }
]

### Example 2 — interpretation (LLM inferred beyond direct statement)
Transcript: "I felt a bit off after eating the curd rice."
Output:
[
  {
    "claimText": "Patient may have had a food-related reaction after eating curd rice.",
    "eventType": "possibleFoodTrigger",
    "evidenceText": "felt a bit off after eating the curd rice",
    "confidence": 0.48,
    "extractionType": "interpretation",
    "missingInfo": ["specific symptoms", "severity", "duration", "trigger confirmed"],
    "riskLevel": "needs-review",
    "safetyStatus": "needsReview",
    "eventTime": null
  }
]

### Example 3 — patientConcern downgrade (§17.3)
Transcript: "I think I have food poisoning."
Output:
[
  {
    "claimText": "Patient believes symptoms may be related to food poisoning. Diagnosis not confirmed.",
    "eventType": "patientConcern",
    "evidenceText": "I think I have food poisoning",
    "confidence": 0.88,
    "extractionType": "direct",
    "missingInfo": ["specific symptoms", "food source", "onset time", "associated symptoms"],
    "riskLevel": "low",
    "safetyStatus": "diagnosisNotConfirmed",
    "eventTime": null
  }
]

Now extract clinical claims from the transcript below. Return ONLY the JSON array.\
"""

PROMPT_VERSION_HASH: str = hashlib.sha256(_SYSTEM_PROMPT.encode()).hexdigest()

_client: anthropic.Anthropic = anthropic.Anthropic()

_CACHED_SYSTEM_BLOCK: list[dict] = [
    {
        "type": "text",
        "text": _SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "not", "no", "nor", "so",
    "yet", "both", "either", "neither", "each", "few", "more", "most",
    "other", "some", "such", "than", "too", "very", "s", "t", "just",
    "patient", "reported", "felt", "feel", "said", "says",
}


def _content_word_overlap(claim_text: str, evidence_text: str) -> float:
    """Return content-word overlap ratio for extractionType validation (Appendix A.1)."""
    def _words(text: str) -> set[str]:
        tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        return {t for t in tokens if t not in _STOP_WORDS}

    claim_words = _words(claim_text)
    evidence_words = _words(evidence_text)
    if not evidence_words:
        return 0.0
    shared = claim_words & evidence_words
    return len(shared) / len(evidence_words)


def _check_cache_threshold() -> None:
    """Assert cached system prompt meets model-specific token threshold.

    Raises RuntimeError before FastAPI binds if the prompt is too short to cache.
    Called at module import time (below).
    """
    min_tokens = MIN_CACHE_TOKENS_BY_MODEL.get(MODEL_ID, 1024)
    result = _client.messages.count_tokens(
        model=MODEL_ID,
        system=_CACHED_SYSTEM_BLOCK,
        messages=[{"role": "user", "content": "test"}],
    )
    if result.input_tokens < min_tokens:
        raise RuntimeError(
            f"Cached system prompt has {result.input_tokens} tokens "
            f"(threshold for {MODEL_ID}: {min_tokens}). "
            "Pad the prompt with additional style/wording examples."
        )


def _parse_llm_output(
    raw: str, input_id: str, patient_id: str, raw_text: str
) -> list[ClinicalClaim] | None:
    """Parse LLM JSON output into ClinicalClaim objects with evidence validation.

    Returns None on malformed JSON (triggers retry), [] on valid empty result.
    """
    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            return None
    except json.JSONDecodeError:
        return None

    claims: list[ClinicalClaim] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        evidence_text = item.get("evidenceText", "")
        try:
            start, end = locate_evidence(evidence_text, raw_text)
        except EvidenceNotFound:
            # §2 non-negotiable: drop claims without verifiable evidence
            continue

        raw_extraction_type = item.get("extractionType", "interpretation")
        overlap = _content_word_overlap(item.get("claimText", ""), evidence_text)
        if overlap < 0.5:
            extraction_type = ExtractionType.INTERPRETATION
        else:
            try:
                extraction_type = ExtractionType(raw_extraction_type)
            except ValueError:
                extraction_type = ExtractionType.INTERPRETATION

        raw_risk = item.get("riskLevel", "needs-review")
        try:
            risk_level = RiskLevel(raw_risk)
        except ValueError:
            risk_level = RiskLevel.NEEDS_REVIEW

        if extraction_type == ExtractionType.INTERPRETATION:
            risk_level = RiskLevel.NEEDS_REVIEW

        raw_event_type = item.get("eventType", "unknownHealthNote")
        try:
            event_type = EventType(raw_event_type)
        except ValueError:
            event_type = EventType.UNKNOWN_HEALTH_NOTE

        raw_safety = item.get("safetyStatus", "safe")
        try:
            safety_status = SafetyStatus(raw_safety)
        except ValueError:
            safety_status = SafetyStatus.SAFE

        confidence = float(item.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        display_warning: str | None = None
        if extraction_type == ExtractionType.INTERPRETATION:
            display_warning = "Interpretation, not a direct quote — review carefully."
        elif confidence < 0.4:
            display_warning = "Low confidence. Needs review."

        claims.append(ClinicalClaim(
            claimId=str(uuid.uuid4()),
            patientId=patient_id,
            inputId=input_id,
            claimText=item.get("claimText", "Unknown event."),
            eventType=event_type,
            eventTime=item.get("eventTime"),
            confidence=confidence,
            evidence=Evidence(
                evidenceText=evidence_text,
                sourceType=InputType.TEXT,
                sourceId=input_id,
                startChar=start,
                endChar=end,
            ),
            missingInfo=item.get("missingInfo", []),
            riskLevel=risk_level,
            safetyStatus=safety_status,
            doctorReviewStatus=DoctorReviewStatus.PENDING,
            extractionType=extraction_type,
            displayWarning=display_warning,
            createdAt=datetime.now(tz=timezone.utc),
        ))

    return claims


def extract_claims_from_text(
    raw_text: str,
    patient_id: str,
    input_id: str,
    context: TrackingContext | None = None,
) -> list[ClinicalClaim]:
    """Call Claude with cached system prompt; parse and validate claims.

    Retries once on malformed JSON (OQ6). Raises ValueError on second failure.
    """
    user_content = f"Transcript:\n{raw_text}"
    if context and (context.activeTrackingPlan or context.activeMedications):
        parts = ["Transcript:", raw_text, ""]
        if context.activeTrackingPlan:
            parts.append(f"Active tracking plan: {context.activeTrackingPlan}")
        if context.activeMedications:
            parts.append(f"Active medications: {', '.join(context.activeMedications)}")
        user_content = "\n".join(parts)

    messages = [{"role": "user", "content": user_content}]

    response = _client.messages.create(
        model=MODEL_ID,
        max_tokens=4096,
        system=_CACHED_SYSTEM_BLOCK,
        messages=messages,
    )
    raw_output = response.content[0].text

    claims = _parse_llm_output(raw_output, input_id, patient_id, raw_text)
    if claims is not None:
        return claims

    # Retry once on malformed JSON (same cached system prompt → cache hit preserved)
    retry_messages = messages + [
        {"role": "assistant", "content": raw_output},
        {
            "role": "user",
            "content": (
                "Your previous response was malformed or not a valid JSON array. "
                "Return ONLY the JSON array with no other text."
            ),
        },
    ]
    retry_response = _client.messages.create(
        model=MODEL_ID,
        max_tokens=4096,
        system=_CACHED_SYSTEM_BLOCK,
        messages=retry_messages,
    )
    retry_output = retry_response.content[0].text
    retry_claims = _parse_llm_output(retry_output, input_id, patient_id, raw_text)

    if retry_claims is None:
        raise ValueError(
            f"LLM returned malformed JSON twice for input_id={input_id}. "
            "Check server logs for details."
        )

    return retry_claims


# Module-import assertion — runs before FastAPI binds (pilot.md C2/H7).
# Skipped when ANTHROPIC_API_KEY is absent (CI/test environments without credentials).
if os.environ.get("ANTHROPIC_API_KEY"):
    _check_cache_threshold()
