"""§8.3 — Confidence Scoring.

Direct statement -> high; ambiguous -> medium; inference -> low; missing
evidence -> rejected or flagged. Diagnosis-style inference must be
downgraded.

The full input is needed (not just the evidence span) to tell direct
statement from inference.
"""

from app.models import Evidence, PatientInput

DIRECT_THRESHOLD = 0.85
AMBIGUOUS_THRESHOLD = 0.6
LOW_CONFIDENCE_THRESHOLD = 0.5


def score_confidence(
    claim_text: str,
    evidence: Evidence | None,
    patient_input: PatientInput,
) -> float:
    raise NotImplementedError


def needs_review(confidence: float) -> bool:
    """True when the claim must be hidden or marked low-confidence (§17.5)."""
    return confidence < LOW_CONFIDENCE_THRESHOLD
