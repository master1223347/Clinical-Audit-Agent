"""§15 / §10.6 — Quality metrics aggregation.

Computes the metrics surfaced on the doctor / clinic quality dashboard from
claims, feedback, and safety blocks.
"""

from app.metrics import QualityMetrics
from app.models import ClinicalClaim, DoctorFeedback, SafetyBlock


def compute_metrics(
    claims: list[ClinicalClaim],
    feedback: list[DoctorFeedback],
    safety_blocks: list[SafetyBlock],
) -> QualityMetrics:
    raise NotImplementedError
