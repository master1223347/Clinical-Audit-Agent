from pydantic import BaseModel


class FollowUpQuestion(BaseModel):
    """§8.5 — a single follow-up question shown to the patient."""

    question: str
    purpose: str
    priority: str  # "high" | "medium" | "low"
