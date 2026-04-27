"""§8.7 — categories of advice the system must never produce.

Every entry in `BLOCKED_CATEGORIES` should have a corresponding entry in
`SAFE_REPLACEMENTS` so `safety.safe_replacement_for` always returns text.
"""

DIAGNOSIS_CLAIM = "diagnosisClaim"
MEDICATION_STOP = "medicationStopAdvice"
MEDICATION_START = "medicationStartAdvice"
DOSE_INCREASE = "doseIncreaseAdvice"
DOSE_DECREASE = "doseDecreaseAdvice"
TAPERING = "taperingAdvice"
EMERGENCY_REASSURANCE = "emergencyReassuranceWithRedFlag"
CERTAINTY_NO_EVIDENCE = "certaintyWithoutEvidence"
REPLACING_CLINICIAN = "replacingClinician"
ADVISING_AGAINST_CARE = "advisingAgainstCare"

BLOCKED_CATEGORIES: list[str] = [
    DIAGNOSIS_CLAIM,
    MEDICATION_STOP,
    MEDICATION_START,
    DOSE_INCREASE,
    DOSE_DECREASE,
    TAPERING,
    EMERGENCY_REASSURANCE,
    CERTAINTY_NO_EVIDENCE,
    REPLACING_CLINICIAN,
    ADVISING_AGAINST_CARE,
]

_MED_CHANGE_REPLACEMENT = (
    "I cannot recommend changing a prescribed medication. "
    "I can log that you skipped a dose and help you prepare a message for your doctor."
)

_DIAGNOSIS_REPLACEMENT = (
    "I cannot diagnose the cause of your symptoms. "
    "I can record the pattern and include it in your doctor report."
)

_REDFLAG_REASSURANCE_REPLACEMENT = (
    "Because you reported a possible red flag, "
    "consider contacting a medical professional promptly."
)

SAFE_REPLACEMENTS: dict[str, str] = {
    DIAGNOSIS_CLAIM: _DIAGNOSIS_REPLACEMENT,
    MEDICATION_STOP: _MED_CHANGE_REPLACEMENT,
    MEDICATION_START: _MED_CHANGE_REPLACEMENT,
    DOSE_INCREASE: _MED_CHANGE_REPLACEMENT,
    DOSE_DECREASE: _MED_CHANGE_REPLACEMENT,
    TAPERING: _MED_CHANGE_REPLACEMENT,
    EMERGENCY_REASSURANCE: _REDFLAG_REASSURANCE_REPLACEMENT,
    CERTAINTY_NO_EVIDENCE: _DIAGNOSIS_REPLACEMENT,
    REPLACING_CLINICIAN: _DIAGNOSIS_REPLACEMENT,
    ADVISING_AGAINST_CARE: _REDFLAG_REASSURANCE_REPLACEMENT,
}
