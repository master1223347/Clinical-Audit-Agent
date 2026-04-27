"""§8.5 — Follow Up Question Generator.

Smallest useful set, prioritized by red-flag relevance, medication safety,
doctor usefulness, missing-field importance, and tracking-plan relevance.
"""

from app.models import ClinicalClaim, FollowUpQuestion, RiskAssessment
from app.models.context import TrackingContext

DEFAULT_MAX_QUESTIONS = 3


def generate_follow_ups(
    claims: list[ClinicalClaim],
    risk: RiskAssessment | None = None,
    context: TrackingContext | None = None,
    max_questions: int = DEFAULT_MAX_QUESTIONS,
) -> list[FollowUpQuestion]:
    raise NotImplementedError
