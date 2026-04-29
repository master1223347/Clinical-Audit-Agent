"""§8.5 — Follow-up question generator tests."""

from datetime import datetime, timezone

from app.core.follow_up import generate_follow_ups
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
    event_type: EventType,
    missing_info: list[str],
    risk_level: RiskLevel = RiskLevel.MEDIUM,
) -> ClinicalClaim:
    return ClinicalClaim(
        claimId="c1",
        patientId="p1",
        inputId="i1",
        claimText="Patient reported vomiting.",
        eventType=event_type,
        confidence=0.9,
        evidence=Evidence(
            evidenceText="threw up",
            sourceType=InputType.TEXT,
            sourceId="i1",
            startChar=0,
            endChar=8,
        ),
        missingInfo=missing_info,
        riskLevel=risk_level,
        safetyStatus=SafetyStatus.SAFE,
        doctorReviewStatus=DoctorReviewStatus.PENDING,
        extractionType=ExtractionType.DIRECT,
        createdAt=datetime.now(tz=timezone.utc),
    )


def test_generates_questions_from_missing_info() -> None:
    claim = _make_claim(
        EventType.VOMITING,
        ["blood in vomit", "hydration status", "duration"],
    )

    questions = generate_follow_ups([claim])

    assert len(questions) > 0
    all_text = " ".join(q.question for q in questions)
    assert any("blood" in q.question.lower() for q in questions)


def test_respects_max_questions_limit() -> None:
    claim = _make_claim(
        EventType.VOMITING,
        ["a", "b", "c", "d", "e", "f"],
    )

    questions = generate_follow_ups([claim], max_questions=3)

    assert len(questions) <= 3


def test_empty_claims_returns_empty() -> None:
    questions = generate_follow_ups([])
    assert questions == []


def test_high_risk_produces_questions() -> None:
    claim = _make_claim(
        EventType.VOMITING,
        ["blood in vomit"],
        risk_level=RiskLevel.HIGH,
    )

    questions = generate_follow_ups([claim])

    assert len(questions) > 0


def test_questions_have_required_fields() -> None:
    claim = _make_claim(EventType.MISSED_MEDICATION, ["medication name", "dose"])

    questions = generate_follow_ups([claim])

    for q in questions:
        assert q.question
        assert q.purpose
        assert q.priority in ("high", "medium", "low")


def test_missed_medication_generates_question() -> None:
    claim = _make_claim(EventType.MISSED_MEDICATION, ["medication name"])

    questions = generate_follow_ups([claim])

    assert len(questions) > 0
