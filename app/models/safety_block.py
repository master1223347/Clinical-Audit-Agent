from datetime import datetime

from pydantic import BaseModel


class SafetyBlock(BaseModel):
    """§9.4 — a record of unsafe output that was blocked and replaced."""

    safetyBlockId: str
    patientId: str
    inputId: str
    blockedText: str
    blockedReason: str
    safeReplacement: str
    createdAt: datetime
