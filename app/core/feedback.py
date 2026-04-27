"""§8.9 — Doctor Feedback Memory.

Apply a doctor action (accept/edit/reject) to a claim and persist feedback.
Edited claims keep both the original AI text (`originalClaimText`) and the
corrected version (`claimText`).
"""

from app.models import ClinicalClaim, DoctorFeedback
from app.models.enums import DoctorAction


def apply_review(
    claim: ClinicalClaim,
    doctor_id: str,
    action: DoctorAction,
    corrected_claim: str | None = None,
    reason: str | None = None,
) -> tuple[ClinicalClaim, DoctorFeedback]:
    """Returns the updated claim and the feedback record to persist.

    For `EDITED`: claim.originalClaimText <- old claim.claimText,
    claim.claimText <- corrected_claim.
    For `REJECTED`: claim is excluded from reports but still kept for quality.
    """
    raise NotImplementedError


def final_claim_text(claim: ClinicalClaim) -> str:
    """Text that appears in the doctor report (edited overrides original)."""
    return claim.claimText
