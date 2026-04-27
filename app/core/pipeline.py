"""End-to-end orchestrator for §7.1 patient input flow.

Pipeline stages, in order:
    intake.normalize_input          (voice/image -> text)
    extraction.extract_claims       (§8.1)
    evidence.locate_evidence        (§8.2; reject claims without it)
    confidence.score_confidence     (§8.3)
    missing_info.detect_missing_info(§8.4)
    contradictions.detect_contradictions (§17.2)
    red_flags.assess_risk           (§8.6)
    safety.screen_output            (§8.7) on every patient/doctor-facing string
    follow_up.generate_follow_ups   (§8.5)
    patient_view.render_for_patient (§7.1 patient surface)
"""

from pydantic import BaseModel, Field

from app.core.patient_view import PatientFacingResult
from app.models import (
    ClinicalClaim,
    FollowUpQuestion,
    PatientInput,
    RiskAssessment,
    SafetyBlock,
)
from app.models.context import TrackingContext


class AnalysisResult(BaseModel):
    """Internal pipeline result; the API converts this into AnalyzeResponse."""

    inputId: str
    claims: list[ClinicalClaim]
    riskAssessment: RiskAssessment | None = None
    followUpQuestions: list[FollowUpQuestion] = Field(default_factory=list)
    safetyBlocks: list[SafetyBlock] = Field(default_factory=list)
    patientFacing: PatientFacingResult | None = None


def analyze(
    patient_input: PatientInput,
    context: TrackingContext | None = None,
) -> AnalysisResult:
    raise NotImplementedError
