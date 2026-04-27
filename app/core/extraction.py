"""§8.1 — Clinical Event Extraction.

Identify clinically relevant events in patient input and emit structured
claims. Every emitted claim must carry evidence (§8.2), confidence (§8.3),
missing info (§8.4), risk level (§8.6), and safety status (§8.7).

`context` carries the doctor's tracking plan and active medications so
extraction can prioritize events that match the care plan.
"""

from app.models import ClinicalClaim, PatientInput
from app.models.context import TrackingContext


def extract_claims(
    patient_input: PatientInput,
    context: TrackingContext | None = None,
) -> list[ClinicalClaim]:
    raise NotImplementedError
