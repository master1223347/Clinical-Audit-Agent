"""§17.2 — Contradictory input detection.

When the patient gives conflicting facts ("had a fever but also no fever"),
emit a single claim that records the conflict and asks for the missing
disambiguating field rather than guessing.
"""

from app.models import ClinicalClaim, PatientInput


def detect_contradictions(
    patient_input: PatientInput, claims: list[ClinicalClaim]
) -> list[ClinicalClaim]:
    """Returns extra claims (or replacements) that flag detected conflicts."""
    raise NotImplementedError
