from pydantic import BaseModel, Field

from app.models.enums import RiskLevel


class RiskAssessment(BaseModel):
    """§9.3 — aggregate risk over a set of claims."""

    riskAssessmentId: str
    patientId: str
    claimIds: list[str]
    riskLevel: RiskLevel
    reasons: list[str] = Field(default_factory=list)
    urgentRedFlagsFound: bool = False
    missingCriticalInfo: list[str] = Field(default_factory=list)
    patientMessage: str
