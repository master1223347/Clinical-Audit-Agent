"""§19 Phase 5 — Longitudinal pattern detection.

Looks across many verified claims to surface repeating triggers, adherence
patterns, and trends. Patterns must be doctor-reviewable and worded as
"observed, not diagnosis."
"""

from app.models import ClinicalClaim, PatternCard


def detect_patterns(claims: list[ClinicalClaim], patient_id: str) -> list[PatternCard]:
    raise NotImplementedError
