"""§8.5 — Follow Up Question Generator.

Generates the smallest useful set of follow-up questions from missing_info fields,
prioritized by: red-flag relevance, medication safety, doctor usefulness, field
importance, and tracking-plan relevance.
"""

from app.models.claim import ClinicalClaim
from app.models.context import TrackingContext
from app.models.follow_up import FollowUpQuestion
from app.models.risk import RiskAssessment

DEFAULT_MAX_QUESTIONS = 3

_HIGH_PRIORITY_FIELDS = {
    "blood in vomit",
    "blood",
    "hydration status",
    "medication name",
    "dose",
    "breathing",
    "consciousness",
    "fever status",
}

_MED_PRIORITY_FIELDS = {
    "duration",
    "severity",
    "scheduled time",
    "reason for missing dose",
    "food trigger",
    "vomiting count",
}

_QUESTION_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "blood in vomit": (
        "Was there any blood in the vomit?",
        "Screen for urgent red flag",
        "high",
    ),
    "blood": (
        "Was there any blood present?",
        "Screen for urgent red flag",
        "high",
    ),
    "hydration status": (
        "Were you able to keep fluids down after vomiting?",
        "Check dehydration risk",
        "high",
    ),
    "medication name": (
        "Which medication did you skip or miss?",
        "Clarify medication adherence",
        "medium",
    ),
    "dose": (
        "What is the usual dose you take?",
        "Clarify medication details",
        "medium",
    ),
    "breathing": (
        "Are you having any difficulty breathing?",
        "Screen for respiratory red flag",
        "high",
    ),
    "consciousness": (
        "Did you lose consciousness or feel faint?",
        "Screen for urgent red flag",
        "high",
    ),
    "fever status": (
        "Do you have a fever or has your temperature been checked?",
        "Determine fever presence",
        "medium",
    ),
    "duration": (
        "How long have you been experiencing these symptoms?",
        "Understand symptom timeline",
        "medium",
    ),
    "severity": (
        "On a scale of 1 to 10, how severe are your symptoms?",
        "Gauge symptom severity",
        "medium",
    ),
    "scheduled time": (
        "When was the dose supposed to be taken?",
        "Clarify missed-dose timing",
        "medium",
    ),
    "reason for missing dose": (
        "Why did you miss the dose?",
        "Understand adherence barrier",
        "medium",
    ),
    "food trigger": (
        "Did you notice if symptoms started after eating a particular food?",
        "Identify possible food trigger",
        "medium",
    ),
    "vomiting count": (
        "How many times did you vomit?",
        "Quantify vomiting episodes",
        "medium",
    ),
    "specific symptoms": (
        "Can you describe your symptoms in more detail?",
        "Gather more clinical detail",
        "medium",
    ),
    "time of onset": (
        "When did your symptoms start?",
        "Establish symptom onset",
        "medium",
    ),
    "whether patient resumed medication": (
        "Have you resumed taking the medication since skipping it?",
        "Check adherence recovery",
        "medium",
    ),
}


def _priority_order(field: str) -> int:
    """Lower number = higher priority."""
    if field in _HIGH_PRIORITY_FIELDS:
        return 0
    if field in _MED_PRIORITY_FIELDS:
        return 1
    return 2


def generate_follow_ups(
    claims: list[ClinicalClaim],
    risk: RiskAssessment | None = None,
    context: TrackingContext | None = None,
    max_questions: int = DEFAULT_MAX_QUESTIONS,
) -> list[FollowUpQuestion]:
    """Return up to max_questions prioritized follow-up questions."""
    if not claims:
        return []

    seen_fields: set[str] = set()
    candidates: list[tuple[int, str]] = []  # (priority, field)

    for claim in claims:
        for field in claim.missingInfo:
            key = field.lower().strip()
            if key not in seen_fields:
                seen_fields.add(key)
                candidates.append((_priority_order(key), key))

    candidates.sort(key=lambda t: t[0])

    questions: list[FollowUpQuestion] = []
    for _prio, field in candidates:
        if len(questions) >= max_questions:
            break
        if field in _QUESTION_TEMPLATES:
            q_text, purpose, priority = _QUESTION_TEMPLATES[field]
        else:
            q_text = f"Can you provide more information about {field}?"
            purpose = f"Clarify {field}"
            priority = "low"
        questions.append(FollowUpQuestion(question=q_text, purpose=purpose, priority=priority))

    return questions
