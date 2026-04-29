"""Missed-escalation regression: every expected_red_flag_rules entry must be covered.

Fixture mode: for each expected_red_flag_rules entry in pilot-set-labels.json,
the corresponding entry in sample-analyze-responses.json must have either
escalationMessage or redFlagOnlySpans (or both). A missing coverage entry means
the eval harness would count a missed escalation as passing — that is a critical
false negative for bar #7.

100% line+branch coverage required.
"""
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
PILOT_LABELS_PATH = _ROOT / "docs/eval/pilot-set-labels.json"
FIXTURE_RESPONSES_PATH = _ROOT / "docs/eval/fixtures/sample-analyze-responses.json"


@pytest.fixture(scope="module")
def pilot_labels():
    with open(PILOT_LABELS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def fixture_responses():
    with open(FIXTURE_RESPONSES_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def response_by_id(fixture_responses) -> dict:
    return {r["inputId"]: r for r in fixture_responses}


def test_all_red_flag_rules_have_fixture_coverage(pilot_labels, response_by_id):
    """For every expected_red_flag_rules entry, the fixture response has escalation or spans."""
    uncovered: list[str] = []
    for tid, label in pilot_labels["labels"].items():
        rules = label.get("expected_red_flag_rules", [])
        if not rules:
            continue
        resp = response_by_id.get(tid)
        if resp is None:
            uncovered.append(
                f"transcript={tid!r} rules={rules}: no fixture response in sample-analyze-responses.json"
            )
            continue
        has_escalation = bool(resp.get("escalationMessage"))
        has_spans = bool(resp.get("redFlagOnlySpans"))
        if not (has_escalation or has_spans):
            uncovered.append(
                f"transcript={tid!r} rules={rules}: fixture response has neither "
                "escalationMessage nor redFlagOnlySpans"
            )
    assert not uncovered, (
        "Missed-escalation gaps in fixture coverage:\n" + "\n".join(f"  {e}" for e in uncovered)
    )


def test_urgent_transcripts_have_fixture_responses(pilot_labels, response_by_id):
    """Every transcript with expected_urgent_claim=true must have a fixture analyze_response."""
    urgent = [
        tid for tid, label in pilot_labels["labels"].items()
        if label.get("expected_urgent_claim", False)
    ]
    missing = [tid for tid in urgent if tid not in response_by_id]
    assert not missing, (
        f"Urgent transcripts without fixture analyze_response: {missing}. "
        "Add entries to docs/eval/fixtures/sample-analyze-responses.json so bar #6 can run."
    )


def test_urgent_fixture_responses_have_escalation_message(pilot_labels, response_by_id):
    """Every fixture response for an urgent transcript must have escalationMessage set (bar #6 guard)."""
    urgent = [
        tid for tid, label in pilot_labels["labels"].items()
        if label.get("expected_urgent_claim", False)
    ]
    missing_escalation = [
        tid for tid in urgent
        if not response_by_id.get(tid, {}).get("escalationMessage")
    ]
    assert not missing_escalation, (
        f"Urgent transcripts with fixture response but no escalationMessage: {missing_escalation}. "
        "The §13.4 escalation message must be present in the fixture for bar #6 to pass."
    )
