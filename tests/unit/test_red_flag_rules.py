"""§8.6 — Red-flag rule matching tests."""

import pytest

from app.rules.red_flag_rules import match_red_flags


def test_match_blood_in_vomit() -> None:
    raw = "I had blood in my vomit this morning."
    matches = match_red_flags(raw)
    keys = [m[0] for m in matches]
    assert "blood_in_vomit" in keys


def test_match_severe_dehydration() -> None:
    matches = match_red_flags("I have severe dehydration and cannot drink water.")
    keys = [m[0] for m in matches]
    assert "severe_dehydration" in keys


def test_match_unable_to_keep_fluids_down() -> None:
    matches = match_red_flags("I cannot keep fluids down at all.")
    keys = [m[0] for m in matches]
    assert "unable_to_keep_fluids" in keys


def test_match_persistent_vomiting() -> None:
    matches = match_red_flags("I have been vomiting persistently for hours.")
    keys = [m[0] for m in matches]
    assert "persistent_vomiting" in keys


def test_match_vomiting_with_abdominal_pain() -> None:
    matches = match_red_flags("I am vomiting with severe abdominal pain.")
    keys = [m[0] for m in matches]
    assert "vomiting_severe_abdominal_pain" in keys


def test_match_vomiting_with_confusion() -> None:
    matches = match_red_flags("I am vomiting and feeling confused.")
    keys = [m[0] for m in matches]
    assert "vomiting_confusion" in keys


def test_match_vomiting_with_fainting() -> None:
    matches = match_red_flags("I vomited and then fainted briefly.")
    keys = [m[0] for m in matches]
    assert "vomiting_fainting" in keys


def test_match_high_risk_patient_vomiting() -> None:
    matches = match_red_flags("I am diabetic and have been vomiting since morning.")
    keys = [m[0] for m in matches]
    assert "vomiting_high_risk_patient" in keys


def test_match_stopped_prescribed_medication() -> None:
    matches = match_red_flags("I stopped taking my prescribed medication yesterday.")
    keys = [m[0] for m in matches]
    assert "stopped_prescribed_medication" in keys


def test_match_doubled_dose() -> None:
    matches = match_red_flags("I took a double dose by mistake this morning.")
    keys = [m[0] for m in matches]
    assert "doubled_dose" in keys


def test_match_mixed_medications() -> None:
    matches = match_red_flags("I mixed my medications without asking the doctor.")
    keys = [m[0] for m in matches]
    assert "mixed_medications" in keys


def test_match_serious_side_effects() -> None:
    matches = match_red_flags("I am having serious side effects from the medicine.")
    keys = [m[0] for m in matches]
    assert "serious_side_effects" in keys


def test_match_confused_about_dosage() -> None:
    matches = match_red_flags("I am confused about my dosage instructions.")
    keys = [m[0] for m in matches]
    assert "confused_about_dosage" in keys


def test_no_red_flags_returns_empty() -> None:
    matches = match_red_flags("I had a mild headache this morning.")
    assert matches == []


def test_match_returns_char_offsets() -> None:
    raw = "I had blood in my vomit."
    matches = match_red_flags(raw)
    assert len(matches) > 0
    for rule_key, start, end in matches:
        assert isinstance(rule_key, str)
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert 0 <= start < end <= len(raw)


def test_match_urgent_chest_pain() -> None:
    matches = match_red_flags("I have severe chest pain right now.")
    keys = [m[0] for m in matches]
    assert "chest_pain" in keys


def test_match_urgent_loss_of_consciousness() -> None:
    matches = match_red_flags("I lost consciousness for a few seconds.")
    keys = [m[0] for m in matches]
    assert "loss_of_consciousness" in keys


def test_match_case_insensitive() -> None:
    matches = match_red_flags("I HAD BLOOD IN MY VOMIT.")
    keys = [m[0] for m in matches]
    assert "blood_in_vomit" in keys
