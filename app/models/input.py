from datetime import datetime

from pydantic import BaseModel

from app.models.enums import InputType


class PatientInput(BaseModel):
    """§9.1 — raw input from the patient before extraction."""

    inputId: str
    patientId: str
    inputType: InputType
    rawText: str
    source: str
    createdAt: datetime
