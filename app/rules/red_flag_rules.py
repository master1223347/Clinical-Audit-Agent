"""§8.6 / §13 — explicit red-flag rules.

`RedFlag` pairs a human-readable trigger with the risk level it implies.
The matcher (in `core.red_flags`) walks these per claim/event type.
"""

from dataclasses import dataclass

from app.models.enums import EventType, RiskLevel


@dataclass(frozen=True)
class RedFlag:
    trigger: str
    risk: RiskLevel


VOMITING_RED_FLAGS: list[RedFlag] = [
    RedFlag("blood in vomit", RiskLevel.HIGH),
    RedFlag("severe dehydration", RiskLevel.HIGH),
    RedFlag("unable to keep fluids down", RiskLevel.HIGH),
    RedFlag("persistent vomiting", RiskLevel.MEDIUM),
    RedFlag("vomiting with severe abdominal pain", RiskLevel.HIGH),
    RedFlag("vomiting with confusion", RiskLevel.HIGH),
    RedFlag("vomiting with fainting", RiskLevel.HIGH),
    RedFlag("vomiting in high risk patient", RiskLevel.HIGH),
]

MEDICATION_RED_FLAGS: list[RedFlag] = [
    RedFlag("stopped prescribed medication", RiskLevel.MEDIUM),
    RedFlag("doubled dose", RiskLevel.HIGH),
    RedFlag("mixed medications without guidance", RiskLevel.HIGH),
    RedFlag("serious side effects", RiskLevel.HIGH),
    RedFlag("confused about dosage", RiskLevel.MEDIUM),
]

URGENT_RED_FLAGS: list[RedFlag] = [
    RedFlag("severe breathing difficulty", RiskLevel.URGENT),
    RedFlag("chest pain", RiskLevel.URGENT),
    RedFlag("stroke like symptoms", RiskLevel.URGENT),
    RedFlag("severe allergic reaction", RiskLevel.URGENT),
    RedFlag("loss of consciousness", RiskLevel.URGENT),
    RedFlag("severe dehydration signs", RiskLevel.URGENT),
]

RED_FLAGS_BY_EVENT: dict[EventType, list[RedFlag]] = {
    EventType.VOMITING: VOMITING_RED_FLAGS,
    EventType.MISSED_MEDICATION: MEDICATION_RED_FLAGS,
    EventType.TAKEN_MEDICATION: MEDICATION_RED_FLAGS,
}

ALL_RED_FLAGS: list[RedFlag] = (
    VOMITING_RED_FLAGS + MEDICATION_RED_FLAGS + URGENT_RED_FLAGS
)
