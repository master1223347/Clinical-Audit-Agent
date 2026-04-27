"""§8.10 / §11.3 — Doctor Report Generator.

Build the final report from accepted and edited claims only. Rejected claims
must not appear in the patient-visible report (they may live in an internal
quality log per §7.3 step 4).
"""

from datetime import date

from app.models import ClinicalClaim, DoctorReport


def generate_report(
    patient_id: str,
    claims: list[ClinicalClaim],
    start_date: date,
    end_date: date,
    include_pending: bool = False,
) -> DoctorReport:
    raise NotImplementedError


def filter_for_report(
    claims: list[ClinicalClaim],
    include_pending: bool = False,
) -> list[ClinicalClaim]:
    """Apply §7.3 / §14 inclusion rules: accepted + edited only by default."""
    raise NotImplementedError
