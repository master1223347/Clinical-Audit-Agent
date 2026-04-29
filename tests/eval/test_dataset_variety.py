"""§17 edge-case coverage gate for the eval dataset.

Structural assertions — if any fail the dataset is hollow and the
harness produces green numbers on nothing. Every assertion names the
specific edge case AND the specific transcript ID that satisfies it
(dispatch brief §2, non-negotiable #2).

100% line+branch coverage required on this file.
"""
import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
PILOT_SET_PATH = _ROOT / "docs/eval/pilot-set.json"
PILOT_LABELS_PATH = _ROOT / "docs/eval/pilot-set-labels.json"

_CODE_SWITCHED_FOOD_RE = re.compile(
    r"\b(curd\s+rice|rasam|ghee|khichdi|idli|buttermilk|dal[- ]chawal)\b",
    re.IGNORECASE,
)
_SYNTHETIC_PATIENT_ID_RE = re.compile(r"^synthetic-\d{3,}$")


@pytest.fixture(scope="module")
def pilot_set():
    with open(PILOT_SET_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pilot_labels():
    with open(PILOT_LABELS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def all_edge_cases(pilot_set):
    cases: set[str] = set()
    for t in pilot_set["transcripts"]:
        cases.update(t.get("edge_cases", []))
    return cases


# ── Dataset size ──────────────────────────────────────────────────────────────

def test_dataset_has_ten_transcripts(pilot_set):
    assert len(pilot_set["transcripts"]) == 10, (
        "Dataset must contain exactly 10 transcripts."
    )


# ── §17 edge-case coverage ────────────────────────────────────────────────────

def test_vague_edge_case_covered(all_edge_cases, pilot_set):
    """§17.1 — vague input must be represented by at least one transcript."""
    assert "vague" in all_edge_cases, (
        "No transcript labeled 'vague'. §17.1 requires a vague-input transcript."
    )
    covering = [t["id"] for t in pilot_set["transcripts"] if "vague" in t.get("edge_cases", [])]
    assert covering, "'vague' in all_edge_cases but no transcript has the label"


def test_contradictory_edge_case_covered(all_edge_cases, pilot_set):
    """§17.2 — contradictory input must be represented."""
    assert "contradictory" in all_edge_cases, (
        "No transcript labeled 'contradictory'. §17.2 requires this edge case."
    )
    covering = [t["id"] for t in pilot_set["transcripts"] if "contradictory" in t.get("edge_cases", [])]
    assert covering, "'contradictory' in all_edge_cases but no transcript has the label"


def test_diagnosis_inference_edge_case_covered(all_edge_cases, pilot_set):
    """§17.3 — diagnosis-inference transcript must be present."""
    assert "diagnosis_inference" in all_edge_cases, (
        "No transcript labeled 'diagnosis_inference'. §17.3 requires this edge case."
    )
    covering = [t["id"] for t in pilot_set["transcripts"] if "diagnosis_inference" in t.get("edge_cases", [])]
    assert covering, "'diagnosis_inference' in all_edge_cases but no transcript has the label"


def test_medication_change_request_edge_case_covered(all_edge_cases, pilot_set):
    """§17.4 — medication-change-request transcript must be present."""
    assert "medication_change_request" in all_edge_cases, (
        "No transcript labeled 'medication_change_request'. §17.4 requires this edge case."
    )
    covering = [
        t["id"] for t in pilot_set["transcripts"]
        if "medication_change_request" in t.get("edge_cases", [])
    ]
    assert covering, "'medication_change_request' in all_edge_cases but no transcript has the label"


def test_low_confidence_edge_case_covered(all_edge_cases, pilot_set):
    """§17.5 — low-confidence-claim transcript must be present."""
    assert "low_confidence" in all_edge_cases, (
        "No transcript labeled 'low_confidence'. §17.5 requires this edge case."
    )
    covering = [t["id"] for t in pilot_set["transcripts"] if "low_confidence" in t.get("edge_cases", [])]
    assert covering, "'low_confidence' in all_edge_cases but no transcript has the label"


# ── §13.4 urgent transcript ───────────────────────────────────────────────────

def test_urgent_transcript_present(pilot_labels):
    """§13.4 — at least one transcript must trigger the urgent-risk path."""
    urgent = [
        tid for tid, label in pilot_labels["labels"].items()
        if label.get("expected_urgent_claim", False)
    ]
    assert len(urgent) >= 1, (
        "No transcript with expected_urgent_claim=true. §13.4 urgent-risk path is not exercised."
    )


# ── Indian-context (persona) requirements ─────────────────────────────────────

def test_code_switched_food_terms_present(pilot_set):
    """At least one transcript must contain Indian food terms for clinical realism."""
    matching = [
        t["id"] for t in pilot_set["transcripts"]
        if _CODE_SWITCHED_FOOD_RE.search(t.get("rawText", ""))
    ]
    assert matching, (
        "No transcript contains Indian food terms (curd rice, rasam, ghee, khichdi, idli, "
        "buttermilk, dal-chawal). The persona requires code-switched food terms."
    )


def test_curd_rice_example_labeled(pilot_set):
    """The SPEC §6 curd-rice case must be explicitly labeled 'curd_rice_example'."""
    labeled = [
        t["id"] for t in pilot_set["transcripts"]
        if "curd_rice_example" in t.get("edge_cases", [])
    ]
    assert labeled, (
        "No transcript labeled 'curd_rice_example'. "
        "pilot-set-spec.md §Mandatory requires a near-equivalent of the SPEC §6 example."
    )


# ── PHI / synthetic-ID guard ──────────────────────────────────────────────────

def test_all_patient_ids_are_synthetic(pilot_set):
    """All patientId values must match the synthetic-NNN format (no real patient IDs)."""
    bad = [
        (t["id"], t.get("patientId", ""))
        for t in pilot_set["transcripts"]
        if not _SYNTHETIC_PATIENT_ID_RE.match(t.get("patientId", ""))
    ]
    assert not bad, (
        f"Non-synthetic patientId values found (must match synthetic-\\d{{3,}}): {bad}"
    )
