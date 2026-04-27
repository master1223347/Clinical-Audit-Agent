from pydantic import BaseModel, Field


class TrackingContext(BaseModel):
    """§11.1 request `context` — the doctor-set tracking plan and meds.

    Passed alongside raw input so extraction, risk, and follow-up modules can
    weight against the active care plan.
    """

    activeTrackingPlan: str | None = None
    activeMedications: list[str] = Field(default_factory=list)
    doctorInstructions: str | None = None
    knownConditions: list[str] = Field(default_factory=list)
    isHighRiskPatient: bool = False
