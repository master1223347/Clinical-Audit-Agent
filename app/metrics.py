"""§10.6 / §15 — quality metrics surfaced to the dashboard."""

from pydantic import BaseModel


class QualityMetrics(BaseModel):
    totalInputs: int = 0
    totalClaims: int = 0
    claimsPerInput: float = 0.0
    averageConfidence: float = 0.0
    acceptanceRate: float = 0.0
    editRate: float = 0.0
    rejectionRate: float = 0.0
    safetyBlocksTriggered: int = 0
    redFlagDetections: int = 0
    followUpCompletionRate: float = 0.0
    mostCommonMissingInfo: list[str] = []
    mostCommonRejectedEventTypes: list[str] = []
    averageReviewTimeSeconds: float = 0.0
    reportGenerationRate: float = 0.0
    doctorReportUsageRate: float = 0.0
