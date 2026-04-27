from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AuditAction(str, Enum):
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"
    EXPORTED = "exported"


class AuditLogEntry(BaseModel):
    """§18.7 — immutable record of who did what to a claim or report."""

    auditId: str
    actorId: str  # doctorId or patientId
    actorRole: str  # "doctor" | "patient" | "system"
    targetType: str  # "claim" | "report" | "input"
    targetId: str
    action: AuditAction
    createdAt: datetime
