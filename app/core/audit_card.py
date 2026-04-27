"""§8.8 — Doctor Audit Cards.

Render a ClinicalClaim plus the surrounding follow-ups and original input as
the doctor-facing review card payload.
"""

from pydantic import BaseModel, Field

from app.models import ClinicalClaim, FollowUpQuestion, PatientInput
from app.models.enums import (
    DoctorReviewStatus,
    EventType,
    RiskLevel,
    SafetyStatus,
)


class DoctorAuditCard(BaseModel):
    """§8.8 card fields, in display order."""

    claimId: str
    claimText: str
    eventType: EventType
    evidenceText: str
    confidence: float = Field(ge=0.0, le=1.0)
    riskLevel: RiskLevel
    missingInfo: list[str]
    safetyStatus: SafetyStatus
    safetyNote: str | None = None
    originalPatientInput: str
    followUpQuestions: list[FollowUpQuestion]
    doctorReviewStatus: DoctorReviewStatus


def build_audit_card(
    claim: ClinicalClaim,
    patient_input: PatientInput,
    follow_ups: list[FollowUpQuestion],
) -> DoctorAuditCard:
    raise NotImplementedError
