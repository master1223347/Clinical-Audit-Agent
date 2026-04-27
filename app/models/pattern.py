from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import EventType


class PatternCard(BaseModel):
    """§19 Phase 5 — longitudinal pattern across many events.

    Patterns must use cautious wording: "observed, not diagnosis."
    """

    patternId: str
    patientId: str
    summary: str  # e.g. "Vomiting reported after dairy intake in 4 of 5 events."
    eventTypes: list[EventType] = Field(default_factory=list)
    sourceClaimIds: list[str] = Field(default_factory=list)
    occurrenceCount: int
    sampleSize: int
    firstSeen: date
    lastSeen: date
    needsDoctorReview: bool = True
