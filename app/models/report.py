from datetime import date

from pydantic import BaseModel, Field

from app.models.claim import ClinicalClaim


class TimelineEntry(BaseModel):
    when: str
    description: str


class DoctorReport(BaseModel):
    """§8.10 / §11.3 — final doctor-ready report."""

    reportId: str
    patientId: str
    startDate: date
    endDate: date
    patientSummary: dict = Field(default_factory=dict)
    mainSymptoms: list[str] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    medicationNotes: list[str] = Field(default_factory=list)
    possibleTriggers: list[str] = Field(default_factory=list)
    redFlagReview: dict = Field(default_factory=dict)
    missingInfo: list[str] = Field(default_factory=list)
    verifiedClaims: list[ClinicalClaim] = Field(default_factory=list)
    doctorDiscussionPoints: list[str] = Field(default_factory=list)
