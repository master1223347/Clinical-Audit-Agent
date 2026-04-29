from pydantic import BaseModel, Field


class TrackingContext(BaseModel):
    """§11.1 request `context` — the doctor-set tracking plan and meds.

    Passed alongside raw input so extraction, risk, and follow-up modules can
    weight against the active care plan.

    Fields are length-capped to limit prompt-injection surface when interpolated
    into the LLM user message.
    """

    activeTrackingPlan: str | None = Field(default=None, max_length=500)
    activeMedications: list[str] = Field(default_factory=list, max_length=50)
    doctorInstructions: str | None = Field(default=None, max_length=500)
    knownConditions: list[str] = Field(default_factory=list, max_length=50)
    isHighRiskPatient: bool = False
