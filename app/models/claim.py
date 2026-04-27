from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    DoctorEditOrigin,
    DoctorReviewStatus,
    EventType,
    ExtractionType,
    InputType,
    RiskLevel,
    SafetyStatus,
)


class Evidence(BaseModel):
    """§8.2 — exact span from patient input that supports a claim.

    Field names mirror packages/shared/types.ts byte-for-byte. Optional fields
    are explicit-None to keep the wire shape stable across producers.
    """

    evidenceText: str
    sourceType: InputType
    sourceId: str
    startChar: int | None = None
    endChar: int | None = None
    transcriptOffsetMs: int | None = None
    imageRegion: dict[str, int] | None = None


class ClinicalClaim(BaseModel):
    """§9.2 — structured, doctor-verifiable claim.

    `originalClaimText` is set only on the first doctor edit (§8.9, Appendix
    A.3) and never overwritten by later edits — the audit trail must preserve
    the AI's first answer verbatim alongside the doctor's correction.

    `extractionType` and `doctorEditOrigin` are Appendix A additions:
    extractionType grades how literal the claim is vs. the cited evidence span;
    doctorEditOrigin records the doctor's self-classification when they save an
    edit (minor_wording / correction / external_knowledge_override).
    """

    claimId: str
    patientId: str
    inputId: str
    claimText: str
    originalClaimText: str | None = None
    eventType: EventType
    eventTime: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Evidence
    attributes: dict[str, Any] = Field(default_factory=dict)
    missingInfo: list[str] = Field(default_factory=list)
    riskLevel: RiskLevel
    safetyStatus: SafetyStatus
    doctorReviewStatus: DoctorReviewStatus = DoctorReviewStatus.PENDING
    doctorEditOrigin: DoctorEditOrigin | None = None
    extractionType: ExtractionType
    displayWarning: str | None = None
    createdAt: datetime
