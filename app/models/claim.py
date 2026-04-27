from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    DoctorReviewStatus,
    EventType,
    InputType,
    RiskLevel,
    SafetyStatus,
)


class Evidence(BaseModel):
    """§8.2 — exact span from patient input that supports a claim."""

    evidenceText: str
    sourceType: InputType
    sourceId: str
    startChar: int | None = None
    endChar: int | None = None
    transcriptOffsetMs: int | None = None  # voice
    imageRegion: dict[str, int] | None = None  # image: {x, y, w, h}


class ClinicalClaim(BaseModel):
    """§9.2 — structured, doctor-verifiable claim.

    `originalClaimText` is set only when a doctor edits the claim (§8.9). The
    doctor-facing report uses `claimText` for accepted claims and the edited
    text for edited claims; rejected claims are excluded from the report.
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
    displayWarning: str | None = None
    createdAt: datetime
