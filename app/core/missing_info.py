"""§8.4 — Missing Information Detection.

For each claim, list the clinical fields a doctor would want answered.
The catalog drives both `missingInfo` on a claim and the follow-up
generator (§8.5).
"""

from app.models import ClinicalClaim
from app.models.enums import EventType

REQUIRED_FIELDS_BY_EVENT: dict[EventType, list[str]] = {
    EventType.VOMITING: [
        "vomiting count",
        "duration",
        "blood in vomit",
        "hydration status",
        "food trigger",
        "fever status",
        "medication relation",
    ],
    EventType.NAUSEA: [
        "duration",
        "trigger",
        "associated vomiting",
        "medication relation",
    ],
    EventType.STOMACH_PAIN: [
        "location",
        "severity",
        "duration",
        "trigger",
        "associated symptoms",
    ],
    EventType.FEVER_PRESENT: [
        "current temperature",
        "time fever was measured",
        "duration",
        "associated symptoms",
    ],
    EventType.FEVER_ABSENT: [
        "method of measurement",
        "time measured",
    ],
    EventType.DIZZINESS: [
        "duration",
        "trigger",
        "associated fainting",
        "hydration status",
    ],
    EventType.MISSED_MEDICATION: [
        "medication name",
        "dose",
        "scheduled time",
        "reason for missing dose",
        "whether patient resumed medication",
    ],
    EventType.TAKEN_MEDICATION: [
        "medication name",
        "dose",
        "time taken",
    ],
    EventType.MEAL_LOGGED: [
        "food items",
        "time of meal",
        "symptoms after meal",
    ],
    EventType.POSSIBLE_FOOD_TRIGGER: [
        "food items",
        "time between meal and symptom",
        "prior occurrences",
    ],
    EventType.PAIN_INCREASE: [
        "current severity",
        "prior severity",
        "trigger",
    ],
    EventType.PAIN_DECREASE: [
        "current severity",
        "what helped",
    ],
    EventType.SYMPTOM_IMPROVED: [
        "what helped",
        "duration of improvement",
    ],
    EventType.SYMPTOM_WORSENED: [
        "what changed",
        "current severity",
    ],
    EventType.DOCTOR_INSTRUCTION: [
        "instruction text",
        "instructing doctor",
    ],
    EventType.LAB_REPORT_UPLOADED: [
        "report date",
        "report type",
    ],
    EventType.PATIENT_CONCERN: [
        "specific symptoms",
        "evidence supporting concern",
    ],
    EventType.UNKNOWN_HEALTH_NOTE: [
        "specific symptoms",
        "time of onset",
        "severity",
    ],
}


def detect_missing_info(claim: ClinicalClaim) -> list[str]:
    """Return required-field names that aren't satisfied by claim.attributes."""
    raise NotImplementedError
