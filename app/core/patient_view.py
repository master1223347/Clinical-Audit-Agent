"""§7.1 — Patient-facing simple view.

The patient does not see confidence scores or audit internals by default. They
see logged events, the smallest useful set of follow-ups (§8.5), and a risk-
appropriate message (§13).
"""

from pydantic import BaseModel

from app.models import ClinicalClaim, FollowUpQuestion, RiskAssessment


class PatientFacingResult(BaseModel):
    loggedSummary: str  # e.g. "Logged: Vomiting after dinner, dizziness, missed medication."
    followUpQuestions: list[FollowUpQuestion]
    safetyMessage: str | None = None  # surfaced when risk >= medium


def render_for_patient(
    claims: list[ClinicalClaim],
    risk: RiskAssessment | None,
    follow_ups: list[FollowUpQuestion],
) -> PatientFacingResult:
    raise NotImplementedError
