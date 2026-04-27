"""§8.2 — Evidence Span Grounding.

Every claim must include the exact span from patient input that supports it.
A claim without evidence must be rejected before display or marked needs
review (§8.3 guideline 4).
"""

from app.models import Evidence, PatientInput


def locate_evidence(patient_input: PatientInput, claim_text: str) -> Evidence | None:
    """Search the patient input for the span that grounds `claim_text`."""
    raise NotImplementedError


def has_sufficient_evidence(evidence: Evidence | None, min_chars: int = 3) -> bool:
    """Reject empty or near-empty evidence spans before they reach a doctor."""
    raise NotImplementedError
