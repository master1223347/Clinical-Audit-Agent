"""Request/response schemas for §11 API behaviors."""

import re

from pydantic import BaseModel, Field, field_validator

from app.models.analyze import AnalyzeResponse  # noqa: F401 — re-exported
from app.models.context import TrackingContext
from app.models.enums import DoctorAction, DoctorEditOrigin, DoctorReviewStatus, InputType

_MAX_RAW_TEXT = 20_000
_MAX_CLAIM_TEXT = 2_000
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class AnalyzeRequest(BaseModel):
    """§11.1."""

    patientId: str = Field(max_length=128)
    inputType: InputType = InputType.TEXT
    rawText: str = Field(min_length=1, max_length=_MAX_RAW_TEXT)
    context: TrackingContext = Field(default_factory=TrackingContext)


class ReviewClaimRequest(BaseModel):
    """§11.2 — includes doctorEditOrigin per Appendix A.3."""

    doctorId: str = Field(max_length=128)
    claimId: str
    action: DoctorAction
    correctedClaim: str | None = Field(default=None, max_length=_MAX_CLAIM_TEXT)
    doctorEditOrigin: DoctorEditOrigin | None = None
    reason: str | None = Field(default=None, max_length=1_000)

    @field_validator("claimId")
    @classmethod
    def claim_id_must_be_uuid(cls, v: str) -> str:
        if not _UUID_RE.match(v):
            raise ValueError("claimId must be a UUID")
        return v


class ReviewClaimResponse(BaseModel):
    """§11.2."""

    claimId: str
    doctorReviewStatus: DoctorReviewStatus
    finalClaimText: str


class PrecomputeItem(BaseModel):
    """One transcript entry for POST /precompute."""

    transcript_id: str = Field(max_length=128)
    raw_text: str = Field(min_length=1, max_length=_MAX_RAW_TEXT)
    patient_id: str = Field(default="pilot-patient", max_length=128)
    context: TrackingContext = Field(default_factory=TrackingContext)


class PrecomputeResponse(BaseModel):
    """POST /precompute response."""

    cached: int
    refreshed: int
    total: int
