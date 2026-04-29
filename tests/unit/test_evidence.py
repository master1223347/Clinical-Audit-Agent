"""§8.2 — Evidence span grounding tests."""

import pytest

from app.core.evidence import EvidenceNotFound, locate_evidence


def test_locate_evidence_exact_substring() -> None:
    # Arrange
    raw_text = "Yesterday after dinner I threw up twice and felt dizzy."
    evidence_text = "threw up twice"

    # Act
    start, end = locate_evidence(evidence_text, raw_text)

    # Assert
    assert raw_text[start:end] == evidence_text


def test_locate_evidence_returns_correct_offsets() -> None:
    raw_text = "I skipped my antibiotic because I felt sick."
    evidence_text = "I skipped my antibiotic"

    start, end = locate_evidence(evidence_text, raw_text)

    assert start == 0
    assert end == 23
    assert raw_text[start:end] == evidence_text


def test_locate_evidence_mid_string() -> None:
    raw_text = "Today I felt dizzy and had a headache."
    evidence_text = "felt dizzy"

    start, end = locate_evidence(evidence_text, raw_text)

    assert raw_text[start:end] == "felt dizzy"
    assert start > 0


def test_locate_evidence_raises_when_not_found() -> None:
    raw_text = "I felt fine today."
    evidence_text = "blood in vomit"

    with pytest.raises(EvidenceNotFound):
        locate_evidence(evidence_text, raw_text)


def test_locate_evidence_raises_on_empty_evidence_text() -> None:
    raw_text = "Some text here."

    with pytest.raises(EvidenceNotFound):
        locate_evidence("", raw_text)


def test_locate_evidence_returns_first_occurrence() -> None:
    raw_text = "pain pain severe pain"
    evidence_text = "pain"

    start, end = locate_evidence(evidence_text, raw_text)

    assert start == 0
    assert end == 4


def test_locate_evidence_single_char_raises_when_not_found() -> None:
    with pytest.raises(EvidenceNotFound):
        locate_evidence("z", "abc def ghi")
