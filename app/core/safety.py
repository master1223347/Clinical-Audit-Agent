"""§8.7 / §12 — Unsafe output blocker and wording validator.

Blocks diagnosis claims, medication change advice, dose changes, tapering,
emergency reassurance when red flags exist, and certainty without evidence.
Also enforces §12 wording rules on any text that will be shown to the
patient or written into a doctor report.
"""

from app.models import PatientInput, SafetyBlock


def screen_output(
    patient_input: PatientInput,
    candidate_text: str,
    has_red_flags: bool = False,
) -> SafetyBlock | None:
    """Return a SafetyBlock if `candidate_text` violates §8.7, else None."""
    raise NotImplementedError


def classify_block(candidate_text: str) -> str | None:
    """Return the blocked-category key (see rules.blocked_advice) or None."""
    raise NotImplementedError


def safe_replacement_for(category: str) -> str:
    """Look up the safe replacement for a blocked category."""
    raise NotImplementedError


def validate_wording(text: str) -> tuple[bool, list[str]]:
    """§12 — return (ok, violations). ok is False when disallowed phrases appear."""
    raise NotImplementedError
