from enum import Enum


class InputType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    CONVERSATION = "conversation"


class EventType(str, Enum):
    VOMITING = "vomiting"
    NAUSEA = "nausea"
    STOMACH_PAIN = "stomachPain"
    FEVER_PRESENT = "feverPresent"
    FEVER_ABSENT = "feverAbsent"
    DIZZINESS = "dizziness"
    MISSED_MEDICATION = "missedMedication"
    TAKEN_MEDICATION = "takenMedication"
    MEAL_LOGGED = "mealLogged"
    POSSIBLE_FOOD_TRIGGER = "possibleFoodTrigger"
    PAIN_INCREASE = "painIncrease"
    PAIN_DECREASE = "painDecrease"
    SYMPTOM_IMPROVED = "symptomImproved"
    SYMPTOM_WORSENED = "symptomWorsened"
    DOCTOR_INSTRUCTION = "doctorInstruction"
    LAB_REPORT_UPLOADED = "labReportUploaded"
    PATIENT_CONCERN = "patientConcern"
    UNKNOWN_HEALTH_NOTE = "unknownHealthNote"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SafetyStatus(str, Enum):
    SAFE = "safe"
    MEDICATION_ADVICE_BLOCKED = "medicationAdviceBlocked"
    DIAGNOSIS_NOT_CONFIRMED = "diagnosisNotConfirmed"
    NEEDS_REVIEW = "needsReview"


class DoctorReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class DoctorAction(str, Enum):
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"
