"""§11.2 — POST /review: doctor accepts, edits, or rejects a claim."""

from fastapi import APIRouter

from app.api.schemas import ReviewClaimRequest, ReviewClaimResponse

router = APIRouter(prefix="/review", tags=["review"])


@router.post("", response_model=ReviewClaimResponse)
def review_claim(req: ReviewClaimRequest) -> ReviewClaimResponse:
    raise NotImplementedError
