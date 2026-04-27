"""Request/response schemas for §11 API behaviors.

These wrap internal types — endpoint handlers convert
`pipeline.AnalysisResult` -> `AnalyzeResponse` and so on.
"""

from datetime import date

from pydantic import BaseModel, Field

from app.metrics import QualityMetrics
from app.models import (
    ClinicalClaim,
    DoctorReport,
    FollowUpQuestion,
    PatternCard,
    RiskAssessment,
    SafetyBlock,
    TimelineEntry,
)
from app.models.context import TrackingContext
from app.models.enums import DoctorAction, DoctorReviewStatus, InputType


class AnalyzeRequest(BaseModel):
    """§11.1."""

    patientId: str
    inputType: InputType
    rawText: str
    context: TrackingContext = Field(default_factory=TrackingContext)


class AnalyzeResponse(BaseModel):
    """§11.1."""

    inputId: str
    claims: list[ClinicalClaim]
    riskAssessment: RiskAssessment | None = None
    followUpQuestions: list[FollowUpQuestion] = Field(default_factory=list)
    safetyBlocks: list[SafetyBlock] = Field(default_factory=list)


class ReviewClaimRequest(BaseModel):
    """§11.2."""

    doctorId: str
    claimId: str
    action: DoctorAction
    correctedClaim: str | None = None
    reason: str | None = None


class ReviewClaimResponse(BaseModel):
    """§11.2."""

    claimId: str
    doctorReviewStatus: DoctorReviewStatus
    finalClaimText: str


class GenerateReportRequest(BaseModel):
    """§11.3."""

    patientId: str
    startDate: date
    endDate: date
    includePendingClaims: bool = False


class GenerateReportResponse(BaseModel):
    """§11.3 — concrete shape derived from `DoctorReport`."""

    reportId: str
    patientSummary: dict = Field(default_factory=dict)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    medicationNotes: list[str] = Field(default_factory=list)
    redFlagReview: dict = Field(default_factory=dict)
    missingInfo: list[str] = Field(default_factory=list)
    doctorDiscussionPoints: list[str] = Field(default_factory=list)

    @classmethod
    def from_report(cls, report: DoctorReport) -> "GenerateReportResponse":
        return cls(
            reportId=report.reportId,
            patientSummary=report.patientSummary,
            timeline=report.timeline,
            medicationNotes=report.medicationNotes,
            redFlagReview=report.redFlagReview,
            missingInfo=report.missingInfo,
            doctorDiscussionPoints=report.doctorDiscussionPoints,
        )


class MetricsResponse(BaseModel):
    """§10.6 / §15."""

    metrics: QualityMetrics
    topRejectedEventTypes: list[str] = Field(default_factory=list)
    topMissingFields: list[str] = Field(default_factory=list)


class PatternsResponse(BaseModel):
    """§19 Phase 5."""

    patterns: list[PatternCard]
