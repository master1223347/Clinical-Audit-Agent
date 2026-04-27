"""§8.6 / §13 — Red Flag Detection and Risk Assessment.

Rule-based first; AI is only used to extract the relevant facts. Produces a
RiskAssessment over a set of claims and flags individual claims with their
own riskLevel. Patient messaging comes from `rules.risk_messages`.
"""

from app.models import ClinicalClaim, RiskAssessment
from app.models.context import TrackingContext
from app.models.enums import RiskLevel


def assess_risk(
    claims: list[ClinicalClaim],
    patient_id: str,
    context: TrackingContext | None = None,
) -> RiskAssessment:
    """Aggregate risk across the set of claims from a single input."""
    raise NotImplementedError


def claim_risk_level(claim: ClinicalClaim, context: TrackingContext | None = None) -> RiskLevel:
    """Per-claim risk used to populate ClinicalClaim.riskLevel."""
    raise NotImplementedError
