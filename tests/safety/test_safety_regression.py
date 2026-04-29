"""§8.7 safety regression suite — one test per category in BLOCKED_CATEGORIES.

These tests live in tests/safety/ as required by wt-01.md. 100% category coverage.
"""

import pytest

from app.core.safety import classify_block, screen_output
from app.models.enums import InputType
from app.models.input import PatientInput
from app.rules.blocked_advice import BLOCKED_CATEGORIES
from datetime import datetime, timezone


def _input() -> PatientInput:
    return PatientInput(
        inputId="i-regr",
        patientId="p-regr",
        inputType=InputType.TEXT,
        rawText="regression test input",
        source="patientApp",
        createdAt=datetime.now(tz=timezone.utc),
    )


# One regression test per category — this is the contractual guarantee.

def test_regression_diagnosis_claim_blocked() -> None:
    """diagnosisClaim category is detected and blocked."""
    result = screen_output(_input(), "You have a viral infection.")
    assert result is not None
    assert result.blockedReason == "diagnosisClaim"


def test_regression_medication_stop_blocked() -> None:
    """medicationStopAdvice category is detected and blocked."""
    result = screen_output(_input(), "Stop taking the antibiotic now.")
    assert result is not None
    assert result.blockedReason == "medicationStopAdvice"


def test_regression_medication_start_blocked() -> None:
    """medicationStartAdvice category is detected and blocked."""
    result = screen_output(_input(), "Start taking paracetamol three times daily.")
    assert result is not None
    assert result.blockedReason == "medicationStartAdvice"


def test_regression_dose_increase_blocked() -> None:
    """doseIncreaseAdvice category is detected and blocked."""
    result = screen_output(_input(), "Take more tablets if symptoms persist.")
    assert result is not None
    assert result.blockedReason == "doseIncreaseAdvice"


def test_regression_dose_decrease_blocked() -> None:
    """doseDecreaseAdvice category is detected and blocked."""
    result = screen_output(_input(), "Reduce the dose to one tablet per day.")
    assert result is not None
    assert result.blockedReason == "doseDecreaseAdvice"


def test_regression_tapering_blocked() -> None:
    """taperingAdvice category is detected and blocked."""
    result = screen_output(_input(), "Taper off the steroid over two weeks.")
    assert result is not None
    assert result.blockedReason == "taperingAdvice"


def test_regression_emergency_reassurance_blocked() -> None:
    """emergencyReassuranceWithRedFlag category is detected and blocked."""
    result = screen_output(_input(), "Don't worry, this is nothing serious.")
    assert result is not None
    assert result.blockedReason == "emergencyReassuranceWithRedFlag"


def test_regression_certainty_without_evidence_blocked() -> None:
    """certaintyWithoutEvidence category is detected and blocked."""
    result = screen_output(_input(), "This is definitely caused by the food you ate.")
    assert result is not None
    assert result.blockedReason == "certaintyWithoutEvidence"


def test_regression_replacing_clinician_blocked() -> None:
    """replacingClinician category is detected and blocked."""
    result = screen_output(_input(), "I can tell you what your doctor would say.")
    assert result is not None
    assert result.blockedReason == "replacingClinician"


def test_regression_advising_against_care_blocked() -> None:
    """advisingAgainstCare category is detected and blocked."""
    result = screen_output(_input(), "You don't need to see a doctor for this.")
    assert result is not None
    assert result.blockedReason == "advisingAgainstCare"


def test_all_blocked_categories_covered_by_regression() -> None:
    """Structural check: ensure BLOCKED_CATEGORIES hasn't grown without a regression test."""
    expected_categories = {
        "diagnosisClaim",
        "medicationStopAdvice",
        "medicationStartAdvice",
        "doseIncreaseAdvice",
        "doseDecreaseAdvice",
        "taperingAdvice",
        "emergencyReassuranceWithRedFlag",
        "certaintyWithoutEvidence",
        "replacingClinician",
        "advisingAgainstCare",
    }
    actual_categories = set(BLOCKED_CATEGORIES)
    uncovered = actual_categories - expected_categories
    assert not uncovered, (
        f"New BLOCKED_CATEGORIES entries have no regression test: {uncovered}"
    )
