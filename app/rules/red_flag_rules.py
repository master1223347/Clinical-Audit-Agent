"""§8.6 / §13 — explicit red-flag rules.

`RedFlag` pairs a human-readable trigger with the risk level it implies.
`match_red_flags(raw_text)` runs all rules against raw text and returns
(rule_key, start, end) tuples for each match.
"""

import re
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

# Map from trigger string to a stable rule_key and regex pattern
# rule_key is snake_case for programmatic use
_RULE_MAP: list[tuple[str, str, re.Pattern]] = [
    # vomiting rules
    ("blood_in_vomit", "blood in (my |the |their )?(vomit|vomiting|sick|sickness)", re.compile(
        r"blood in (my |the |their )?(vomit|vomiting|sick|sickness)", re.IGNORECASE
    )),
    ("severe_dehydration", "severe dehydration", re.compile(
        r"severe\s+dehydration", re.IGNORECASE
    )),
    ("unable_to_keep_fluids", "unable to keep fluids", re.compile(
        r"(unable to keep|can.t keep|cannot keep)\s+(any\s+)?(fluids?|water|liquids?)\s*(down)?",
        re.IGNORECASE,
    )),
    ("persistent_vomiting", "persistent vomiting", re.compile(
        r"(persistent(ly)?|continuous(ly)?|keep(ing)?|been)\s+vomiting",
        re.IGNORECASE,
    )),
    ("vomiting_severe_abdominal_pain", "vomiting with severe abdominal pain", re.compile(
        r"vomiting.{0,30}(severe\s+)?(abdominal|stomach|belly)\s+pain",
        re.IGNORECASE,
    )),
    ("vomiting_confusion", "vomiting with confusion", re.compile(
        r"(vomiting.{0,30}(confused|confusion|disoriented)|"
        r"(confused|confusion).{0,30}vomiting)",
        re.IGNORECASE,
    )),
    ("vomiting_fainting", "vomiting with fainting", re.compile(
        r"(vomit(ed|ing).{0,30}(faint(ed|ing)|pass(ed)?\s+out|lost\s+consciousness)|"
        r"(faint(ed|ing)|pass(ed)?\s+out).{0,30}vomit(ed|ing))",
        re.IGNORECASE,
    )),
    ("vomiting_high_risk_patient", "vomiting in high risk patient", re.compile(
        r"(diabetic|diabetes|immunocompromised|cancer|hiv|elderly|pregnant|"
        r"heart\s+disease|kidney\s+disease).{0,60}vomiting|"
        r"vomiting.{0,60}(diabetic|diabetes|immunocompromised|cancer|hiv|elderly|pregnant)",
        re.IGNORECASE,
    )),
    # medication rules
    ("stopped_prescribed_medication", "stopped prescribed medication", re.compile(
        r"(stopped?|quit|discontinued?)\s+(taking|using)?\s*(my\s+|the\s+)?"
        r"(prescribed|medication|medicine|antibiotic|tablet|pill|drug)",
        re.IGNORECASE,
    )),
    ("doubled_dose", "doubled dose", re.compile(
        r"(took|taken|took\s+a?)\s*(double|twice\s+the|two|2)\s*(dose|tablet|pill|amount)",
        re.IGNORECASE,
    )),
    ("mixed_medications", "mixed medications without guidance", re.compile(
        r"(mixed|combining|combined|mix)\s+(my\s+)?(medications?|medicines?|drugs?|tablets?|pills?)"
        r"(\s+without\s+(asking|guidance|doctor|telling))?",
        re.IGNORECASE,
    )),
    ("serious_side_effects", "serious side effects", re.compile(
        r"(serious|severe|bad|dangerous|harmful)\s+side\s+effects?",
        re.IGNORECASE,
    )),
    ("confused_about_dosage", "confused about dosage", re.compile(
        r"confused?\s+about\s+(my\s+|the\s+)?(dosage?|dose|instructions?|how\s+(many|much))",
        re.IGNORECASE,
    )),
    # urgent rules
    ("chest_pain", "chest pain", re.compile(
        r"(severe\s+)?chest\s+pain",
        re.IGNORECASE,
    )),
    ("loss_of_consciousness", "loss of consciousness", re.compile(
        r"(los(t|ing)\s+consciousness|fainted?|pass(ed)?\s+out|"
        r"blacked?\s+out|fell\s+unconscious)",
        re.IGNORECASE,
    )),
    ("severe_breathing_difficulty", "severe breathing difficulty", re.compile(
        r"(severe\s+)?breathing\s+(difficulty|problem|issue|trouble)|"
        r"can.t\s+breathe|difficulty\s+breathing",
        re.IGNORECASE,
    )),
    ("stroke_symptoms", "stroke like symptoms", re.compile(
        r"stroke|"
        r"(sudden|face|arm|leg).{0,20}(numb|weak|droop)|"
        r"slurred?\s+speech",
        re.IGNORECASE,
    )),
    ("severe_allergic_reaction", "severe allergic reaction", re.compile(
        r"(severe|serious|life.threatening)\s+allergic\s+reaction|"
        r"anaphyla(xis|ctic)",
        re.IGNORECASE,
    )),
]


def match_red_flags(raw_text: str) -> list[tuple[str, int, int]]:
    """Scan raw_text for all red-flag rule matches.

    Returns a list of (rule_key, start, end) tuples. Char offsets index into
    raw_text. Multiple matches per rule are all returned.
    """
    results: list[tuple[str, int, int]] = []
    for rule_key, _desc, pattern in _RULE_MAP:
        for m in pattern.finditer(raw_text):
            results.append((rule_key, m.start(), m.end()))
    return results


def is_urgent_match(rule_key: str) -> bool:
    """Return True if this rule_key corresponds to an URGENT risk level."""
    urgent_keys = {
        "chest_pain",
        "loss_of_consciousness",
        "severe_breathing_difficulty",
        "stroke_symptoms",
        "severe_allergic_reaction",
    }
    return rule_key in urgent_keys
