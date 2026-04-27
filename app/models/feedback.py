from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DoctorAction


class DoctorFeedback(BaseModel):
    """§9.5 / §8.9 — doctor review action stored for quality improvement."""

    feedbackId: str
    doctorId: str
    claimId: str
    action: DoctorAction
    originalClaim: str
    correctedClaim: str | None = None
    reason: str | None = None
    createdAt: datetime
