"""§11.2 — POST /review-claim: doctor accepts, edits, or rejects a claim.

CRITICAL: this endpoint MUST NOT touch analyze_responses. Only claims rows are
updated. The structural separation is the sticky-escalation guarantee (pilot.md C4).
"""

from fastapi import APIRouter, HTTPException

from app.api.schemas import ReviewClaimRequest, ReviewClaimResponse
from app.models.enums import DoctorAction, DoctorReviewStatus
from app.storage.deps import get_repo

router = APIRouter(prefix="/review-claim", tags=["review"])


@router.post("", response_model=ReviewClaimResponse)
def review_claim(req: ReviewClaimRequest) -> ReviewClaimResponse:
    """Doctor action — updates claims row ONLY. Never touches analyze_responses."""
    repo = get_repo()

    claim = repo.get_claim(req.claimId)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    new_status: DoctorReviewStatus
    final_claim_text: str = claim["claim_text"]

    if req.action == DoctorAction.ACCEPTED:
        new_status = DoctorReviewStatus.ACCEPTED
        repo.update_claim(
            claim_id=req.claimId,
            doctor_review_status=new_status.value,
            claim_text=None,
            original_claim_text=None,
            doctor_edit_origin=None,
        )

    elif req.action == DoctorAction.EDITED:
        new_status = DoctorReviewStatus.EDITED
        new_text = req.correctedClaim or claim["claim_text"]
        original = claim["claim_text"]  # preserve first AI claim verbatim
        edit_origin = req.doctorEditOrigin.value if req.doctorEditOrigin else None
        repo.update_claim(
            claim_id=req.claimId,
            doctor_review_status=new_status.value,
            claim_text=new_text,
            original_claim_text=original,
            doctor_edit_origin=edit_origin,
        )
        final_claim_text = new_text

    else:  # REJECTED
        new_status = DoctorReviewStatus.REJECTED
        repo.update_claim(
            claim_id=req.claimId,
            doctor_review_status=new_status.value,
            claim_text=None,
            original_claim_text=None,
            doctor_edit_origin=None,
        )

    return ReviewClaimResponse(
        claimId=req.claimId,
        doctorReviewStatus=new_status,
        finalClaimText=final_claim_text,
    )
