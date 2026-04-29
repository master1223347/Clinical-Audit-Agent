"""Dedup policy tests — pilot.md §2 (post-review M2a)."""

from datetime import datetime, timezone

import pytest

from app.core.dedup import dedup_claims
from app.models.claim import ClinicalClaim, Evidence
from app.models.enums import (
    DoctorReviewStatus,
    EventType,
    ExtractionType,
    InputType,
    RiskLevel,
    SafetyStatus,
)


def _make_claim(
    claim_id: str,
    event_type: EventType,
    evidence_text: str,
    start: int,
    end: int,
    confidence: float,
) -> ClinicalClaim:
    return ClinicalClaim(
        claimId=claim_id,
        patientId="patient-test",
        inputId="input-test",
        claimText=f"Patient {evidence_text}.",
        eventType=event_type,
        confidence=confidence,
        evidence=Evidence(
            evidenceText=evidence_text,
            sourceType=InputType.TEXT,
            sourceId="input-test",
            startChar=start,
            endChar=end,
        ),
        riskLevel=RiskLevel.LOW,
        safetyStatus=SafetyStatus.SAFE,
        doctorReviewStatus=DoctorReviewStatus.PENDING,
        extractionType=ExtractionType.DIRECT,
        createdAt=datetime.now(tz=timezone.utc),
    )


def test_dedup_three_same_event_overlapping_returns_highest_confidence() -> None:
    """§2 M2a — 3 candidates → 1 survivor (highest confidence)."""
    # Three claims on same event, overlapping spans
    c1 = _make_claim("c1", EventType.VOMITING, "threw up twice", 10, 24, 0.7)
    c2 = _make_claim("c2", EventType.VOMITING, "threw up twice after dinner", 10, 36, 0.9)
    c3 = _make_claim("c3", EventType.VOMITING, "threw up twice", 10, 24, 0.5)

    result = dedup_claims([c1, c2, c3])

    assert len(result) == 1
    assert result[0].confidence == 0.9
    assert result[0].claimId == "c2"


def test_dedup_different_event_types_preserved() -> None:
    """Claims with different eventTypes are never merged."""
    c1 = _make_claim("c1", EventType.VOMITING, "threw up twice", 10, 24, 0.9)
    c2 = _make_claim("c2", EventType.DIZZINESS, "felt dizzy", 30, 40, 0.8)

    result = dedup_claims([c1, c2])

    assert len(result) == 2


def test_dedup_non_overlapping_spans_preserved() -> None:
    """Two vomiting claims with non-overlapping spans stay separate."""
    c1 = _make_claim("c1", EventType.VOMITING, "threw up", 0, 8, 0.9)
    c2 = _make_claim("c2", EventType.VOMITING, "vomited again", 50, 63, 0.8)

    result = dedup_claims([c1, c2])

    assert len(result) == 2


def test_dedup_empty_list() -> None:
    assert dedup_claims([]) == []


def test_dedup_single_claim_unchanged() -> None:
    c1 = _make_claim("c1", EventType.VOMITING, "threw up", 0, 8, 0.9)
    result = dedup_claims([c1])
    assert len(result) == 1
    assert result[0].claimId == "c1"


def test_dedup_exactly_50_percent_overlap_not_merged() -> None:
    """Boundary: overlap exactly 50% should NOT trigger dedup (>50% required)."""
    # span1: [0, 10] length 10
    # span2: [5, 15] length 10, overlap = 5 = 50%
    c1 = _make_claim("c1", EventType.VOMITING, "0123456789", 0, 10, 0.9)
    c2 = _make_claim("c2", EventType.VOMITING, "56789abcde", 5, 15, 0.8)

    result = dedup_claims([c1, c2])
    # 50% overlap → NOT merged (spec says >50%)
    assert len(result) == 2


def test_dedup_over_50_percent_overlap_merged() -> None:
    """Span overlap just over 50% triggers dedup."""
    # span1: [0, 10] length 10
    # span2: [4, 14] length 10, overlap = 6 = 60%
    c1 = _make_claim("c1", EventType.VOMITING, "0123456789", 0, 10, 0.7)
    c2 = _make_claim("c2", EventType.VOMITING, "456789abcd", 4, 14, 0.9)

    result = dedup_claims([c1, c2])

    assert len(result) == 1
    assert result[0].confidence == 0.9
