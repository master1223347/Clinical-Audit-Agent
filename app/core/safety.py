"""§8.7 / §12 — Unsafe output blocker and wording validator.

Rule-first design: the LLM never authors final patient-facing text in blocked
output paths. All replacement language comes from blocked_advice.SAFE_REPLACEMENTS.
100% line + branch coverage required on this module.
"""

import re
import uuid
from datetime import datetime, timezone

from app.models.input import PatientInput
from app.models.safety_block import SafetyBlock
from app.rules.blocked_advice import (
    ADVISING_AGAINST_CARE,
    BLOCKED_CATEGORIES,
    CERTAINTY_NO_EVIDENCE,
    DIAGNOSIS_CLAIM,
    DOSE_DECREASE,
    DOSE_INCREASE,
    EMERGENCY_REASSURANCE,
    MEDICATION_START,
    MEDICATION_STOP,
    REPLACING_CLINICIAN,
    SAFE_REPLACEMENTS,
    TAPERING,
)

# Pattern map: each category maps to a list of regex patterns (case-insensitive)
_CATEGORY_PATTERNS: dict[str, list[str]] = {
    DIAGNOSIS_CLAIM: [
        r"\byou (have|had|got|are having)\b",
        r"\bthis is (a |an )?(case of|sign of|symptom of|indication of)\b",
        r"\bpatient has\b",
        r"\bdiagnosis\b",
        r"\bprobably have\b",
        r"\blikely have\b",
        r"\bsounds like\b.*\b(infection|illness|poisoning|condition)\b",
        r"\b(viral|bacterial|fungal)\s+(infection|illness|gastroenteritis)\b",
    ],
    MEDICATION_STOP: [
        r"\bstop (taking|your|the)\b",
        r"\bdiscontinue\b",
        r"\bno longer (take|need to take)\b",
        r"\bskip (the|your|remaining)\b.*\b(dose|medication|tablet|pill)\b",
        r"\bcan stop\b",
        r"\bshould stop\b",
    ],
    MEDICATION_START: [
        r"\bstart (taking|using|on)\b",
        r"\bbegin (taking|using)\b",
        r"\btake (ibuprofen|paracetamol|aspirin|antibiotics?|medication|medicine)\b",
        r"\bshould (start|begin|take)\b.*\b(medication|tablet|pill|drug)\b",
    ],
    DOSE_INCREASE: [
        r"\bincrease (the |your )?(dose|dosage|amount)\b",
        r"\btake more\b",
        r"\bdouble (the |your )?(dose|tablet|pill)\b",
        r"\bup (the |your )?(dose|dosage)\b",
    ],
    DOSE_DECREASE: [
        r"\bdecrease (the |your )?(dose|dosage|amount)\b",
        r"\breduce (the |your )?(dose|dosage)\b",
        r"\btake less\b",
        r"\bhalf (the |a )?(dose|tablet|pill)\b",
    ],
    TAPERING: [
        r"\btaper\b",
        r"\bgradually (reduce|decrease|lower|taper)\b",
        r"\bwean (off|down)\b",
        r"\bslowly reduce\b",
    ],
    EMERGENCY_REASSURANCE: [
        r"\b(not|nothing) serious\b",
        r"\bnothing to worry (about)?\b",
        r"\bno (need to|reason to) (worry|panic|be concerned)\b",
        r"\bdon.t worry\b",
        r"\bis fine\b",
        r"\ball is (fine|well|good|ok)\b",
        r"\bnot urgent\b",
        r"\bnot an emergency\b",
    ],
    CERTAINTY_NO_EVIDENCE: [
        r"\bdefinitely (caused|due to|from|because of)\b",
        r"\bcertainly (caused|due to|from|is)\b",
        r"\bwithout (any )?doubt\b",
        r"\bthis is definitely\b",
        r"\bmust be (caused|due to|from)\b",
        r"\bis definitely\b",
    ],
    REPLACING_CLINICIAN: [
        r"\b(i can|i will) (replace|act as|serve as|be) (your )?(doctor|physician|clinician)\b",
        r"\bcan tell you what (your )?doctor would say\b",
        r"\bdon.t need a doctor\b",
        r"\bi am your doctor\b",
        r"\b(as your|acting as) (doctor|physician|clinician)\b",
    ],
    ADVISING_AGAINST_CARE: [
        r"\b(no need|not necessary|don.t need|unnecessary) to see (a )?doctor\b",
        r"\bdon.t (see|visit|contact|go to) (a |your )?(doctor|hospital|emergency|clinic)\b",
        r"\bno need for (medical|a doctor|a physician|hospital)\b",
        r"\b(avoid|skip|don.t bother) (seeing|visiting|going to) (a )?doctor\b",
    ],
}

# §12 disallowed phrases for wording validator
_DISALLOWED_WORDING: list[tuple[str, str]] = [
    (r"\bpatient has\b", "Avoid 'patient has' — use 'patient reported'"),
    (r"\bshould stop (medication|the medication|taking)\b", "Never advise stopping medication"),
    (r"\bdefinitely caused by\b", "Avoid certainty claims"),
    (r"\bnot serious\b", "Never reassure away from medical care"),
    (r"\bno need to see (a )?doctor\b", "Never advise against seeking care"),
    (r"\bincrease the dose\b", "Never advise dose increase"),
    (r"\bdecrease the dose\b", "Never advise dose decrease"),
    (r"\btaper the medication\b", "Never advise tapering"),
    (r"\bfood poisoning\b", "Use 'possible food-related symptoms' not a diagnosis"),
]


def classify_block(candidate_text: str) -> str | None:
    """Return the first blocked-category key or None if the text is safe."""
    lower = candidate_text.lower()
    for category in BLOCKED_CATEGORIES:
        patterns = _CATEGORY_PATTERNS.get(category, [])
        for pattern in patterns:
            if re.search(pattern, lower):
                return category
    return None


def safe_replacement_for(category: str) -> str:
    """Look up the safe replacement for a blocked category."""
    return SAFE_REPLACEMENTS[category]


def screen_output(
    patient_input: PatientInput,
    candidate_text: str,
    has_red_flags: bool = False,
) -> SafetyBlock | None:
    """Return a SafetyBlock if candidate_text violates §8.7, else None.

    The LLM never authors this output — all replacement text comes from
    blocked_advice.SAFE_REPLACEMENTS.
    """
    category = classify_block(candidate_text)
    if category is None:
        return None
    return SafetyBlock(
        safetyBlockId=str(uuid.uuid4()),
        patientId=patient_input.patientId,
        inputId=patient_input.inputId,
        blockedText=candidate_text,
        blockedReason=category,
        safeReplacement=SAFE_REPLACEMENTS[category],
        createdAt=datetime.now(tz=timezone.utc),
    )


def validate_wording(text: str) -> tuple[bool, list[str]]:
    """§12 — return (ok, violations). ok is False when disallowed phrases appear."""
    lower = text.lower()
    violations: list[str] = []
    for pattern, message in _DISALLOWED_WORDING:
        if re.search(pattern, lower):
            violations.append(message)
    return (len(violations) == 0, violations)
