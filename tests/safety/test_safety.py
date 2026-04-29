"""§8.7 — Safety blocker unit tests (100% line + branch coverage required)."""

from datetime import datetime, timezone

import pytest

from app.core.safety import classify_block, safe_replacement_for, screen_output, validate_wording
from app.models.input import PatientInput
from app.models.enums import InputType
from app.rules.blocked_advice import BLOCKED_CATEGORIES, SAFE_REPLACEMENTS


def _make_input(raw_text: str = "test input") -> PatientInput:
    return PatientInput(
        inputId="i1",
        patientId="p1",
        inputType=InputType.TEXT,
        rawText=raw_text,
        source="patientApp",
        createdAt=datetime.now(tz=timezone.utc),
    )


# --- classify_block ---

def test_classify_block_diagnosis_claim() -> None:
    assert classify_block("You probably have food poisoning.") == "diagnosisClaim"


def test_classify_block_medication_stop() -> None:
    assert classify_block("You can stop taking your antibiotic tonight.") == "medicationStopAdvice"


def test_classify_block_medication_start() -> None:
    assert classify_block("You should start taking ibuprofen now.") == "medicationStartAdvice"


def test_classify_block_dose_increase() -> None:
    assert classify_block("Increase your dose if the pain continues.") == "doseIncreaseAdvice"


def test_classify_block_dose_decrease() -> None:
    assert classify_block("You can decrease the dose to half.") == "doseDecreaseAdvice"


def test_classify_block_tapering() -> None:
    assert classify_block("Taper the medication over two weeks.") == "taperingAdvice"


def test_classify_block_emergency_reassurance() -> None:
    assert classify_block("This is nothing serious, no need to worry.") == "emergencyReassuranceWithRedFlag"


def test_classify_block_certainty_no_evidence() -> None:
    assert classify_block("This is definitely caused by the antibiotic.") == "certaintyWithoutEvidence"


def test_classify_block_replacing_clinician() -> None:
    assert classify_block("I can replace your doctor for this decision.") == "replacingClinician"


def test_classify_block_advising_against_care() -> None:
    assert classify_block("There is no need to see a doctor about this.") == "advisingAgainstCare"


def test_classify_block_safe_text_returns_none() -> None:
    assert classify_block("Patient reported vomiting twice after dinner.") is None


def test_classify_block_none_for_plain_log() -> None:
    assert classify_block("Logged: stomach pain after lunch.") is None


# --- safe_replacement_for ---

def test_safe_replacement_for_every_category() -> None:
    for category in BLOCKED_CATEGORIES:
        replacement = safe_replacement_for(category)
        assert isinstance(replacement, str)
        assert len(replacement) > 10


def test_safe_replacement_matches_blocked_advice_dict() -> None:
    for category, expected in SAFE_REPLACEMENTS.items():
        assert safe_replacement_for(category) == expected


# --- screen_output ---

def test_screen_output_returns_safety_block_for_diagnosis() -> None:
    patient_input = _make_input()
    result = screen_output(patient_input, "You probably have food poisoning.")

    assert result is not None
    assert result.blockedReason == "diagnosisClaim"
    assert "cannot diagnose" in result.safeReplacement.lower()


def test_screen_output_returns_none_for_safe_text() -> None:
    patient_input = _make_input()
    result = screen_output(patient_input, "Patient reported vomiting after dinner.")

    assert result is None


def test_screen_output_medication_stop() -> None:
    patient_input = _make_input()
    result = screen_output(patient_input, "You can stop taking your antibiotic.")

    assert result is not None
    assert result.blockedReason == "medicationStopAdvice"


def test_screen_output_with_red_flags_blocks_reassurance() -> None:
    patient_input = _make_input()
    result = screen_output(
        patient_input, "This is not serious at all.", has_red_flags=True
    )

    assert result is not None


def test_screen_output_without_red_flags_still_blocks_reassurance() -> None:
    """Emergency reassurance is blocked regardless of red_flags flag."""
    patient_input = _make_input()
    result = screen_output(
        patient_input, "This is nothing serious.", has_red_flags=False
    )

    assert result is not None
    assert result.blockedReason == "emergencyReassuranceWithRedFlag"


def test_screen_output_safety_block_has_all_fields() -> None:
    patient_input = _make_input("test raw")
    result = screen_output(patient_input, "Stop taking your medication.")

    assert result is not None
    assert result.safetyBlockId
    assert result.patientId == "p1"
    assert result.inputId == "i1"
    assert result.blockedText == "Stop taking your medication."
    assert result.safeReplacement
    assert result.createdAt


def test_screen_output_dose_increase_blocked() -> None:
    result = screen_output(_make_input(), "Increase the dose to 500mg.")
    assert result is not None
    assert result.blockedReason == "doseIncreaseAdvice"


def test_screen_output_tapering_blocked() -> None:
    result = screen_output(_make_input(), "Taper gradually over two weeks.")
    assert result is not None
    assert result.blockedReason == "taperingAdvice"


def test_screen_output_replacing_clinician_blocked() -> None:
    result = screen_output(_make_input(), "I can replace your doctor here.")
    assert result is not None
    assert result.blockedReason == "replacingClinician"


def test_screen_output_advising_against_care_blocked() -> None:
    result = screen_output(_make_input(), "No need to see a doctor about this.")
    assert result is not None
    assert result.blockedReason == "advisingAgainstCare"


# --- validate_wording ---

def test_validate_wording_ok_for_safe_text() -> None:
    ok, violations = validate_wording("Patient reported vomiting after dinner. Cause unknown.")
    assert ok is True
    assert violations == []


def test_validate_wording_flags_diagnosis_language() -> None:
    ok, violations = validate_wording("Patient has food poisoning.")
    assert ok is False
    assert len(violations) > 0


def test_validate_wording_flags_no_need_to_see_doctor() -> None:
    ok, violations = validate_wording("No need to see a doctor.")
    assert ok is False


def test_validate_wording_flags_medication_stop() -> None:
    ok, violations = validate_wording("Patient should stop medication.")
    assert ok is False


def test_validate_wording_flags_increase_dose() -> None:
    ok, violations = validate_wording("Increase the dose.")
    assert ok is False


def test_validate_wording_flags_decrease_dose() -> None:
    ok, violations = validate_wording("Decrease the dose.")
    assert ok is False


def test_validate_wording_flags_taper() -> None:
    ok, violations = validate_wording("Taper the medication.")
    assert ok is False


def test_validate_wording_flags_certainty_language() -> None:
    ok, violations = validate_wording("This is definitely caused by the antibiotic.")
    assert ok is False


def test_validate_wording_allowed_patient_reported() -> None:
    ok, _ = validate_wording("Patient reported feeling dizzy. Cause unknown.")
    assert ok is True


def test_blocked_categories_all_have_safe_replacements() -> None:
    """§8.7 non-negotiable: every BLOCKED_CATEGORIES entry has a SAFE_REPLACEMENTS entry."""
    for category in BLOCKED_CATEGORIES:
        assert category in SAFE_REPLACEMENTS, f"No safe replacement for '{category}'"
