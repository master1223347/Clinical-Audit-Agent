"""Safety regression: every BLOCKED_CATEGORY must be triggered by at least one labeled transcript.

100% line+branch coverage required. If any category lacks a triggering transcript,
the eval harness produces a false green on that safety rule — the harness cannot
detect regressions it has no test input for.

No API call needed — this is purely a dataset-coverage check.
"""
import json
from pathlib import Path

import pytest

from app.rules.blocked_advice import BLOCKED_CATEGORIES

_ROOT = Path(__file__).parent.parent.parent
PILOT_LABELS_PATH = _ROOT / "docs/eval/pilot-set-labels.json"


@pytest.fixture(scope="module")
def pilot_labels():
    with open(PILOT_LABELS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def triggered_categories(pilot_labels) -> set[str]:
    triggered: set[str] = set()
    for label in pilot_labels["labels"].values():
        triggered.update(label.get("expected_safety_categories", []))
    return triggered


@pytest.mark.parametrize("category", BLOCKED_CATEGORIES)
def test_blocked_category_has_triggering_transcript(category: str, triggered_categories: set[str]):
    """Every entry in BLOCKED_CATEGORIES appears in at least one transcript's expected_safety_categories."""
    assert category in triggered_categories, (
        f"BLOCKED_CATEGORY '{category}' has no triggering transcript in pilot-set-labels.json. "
        "Add a transcript whose expected_safety_categories includes this category so the eval "
        "harness can detect a regression in this safety rule."
    )
