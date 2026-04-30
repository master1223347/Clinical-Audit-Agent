"""Unit tests for tests/eval/run_eval.py sub-components.

Verifies bar computations are deterministic against the fixture's labeled actions
(H6 — no random sampling, no simulation function). Every bar is tested for:
  - correct computation against the fixture
  - None-return for the empty / vacuous case
  - determinism (same input → same output)

Also verifies structural guarantees:
  - --mode=live raises NotImplementedError (Phase 3, see wt-03.md step 3.5)
  - zero_claim_transcripts reported in result dict
  - zero-claim transcripts excluded from bars 1-3

Live-mode coverage (Phase 3b, see wt-03.md step 3.5):
  - compute_bar1_live, compute_bar2_live, compute_bar3_live read
    doctorReviewStatus per claim; pending claims excluded from cohort.
  - run_live_mode aggregates /precompute + /analyze/cached responses through
    a httpx.MockTransport — verifies orchestrator wiring without a live server.
  - _render_live_header emits valid JSON with the five required keys.
"""
import json
from pathlib import Path

import httpx
import pytest

# conftest.py in this directory adds tests/eval/ to sys.path so this import works.
from run_eval import (
    EvalMode,
    _render_live_header,
    _render_markdown,
    compute_bar1,
    compute_bar1_live,
    compute_bar2,
    compute_bar2_live,
    compute_bar3,
    compute_bar3_live,
    compute_bar4,
    compute_bar5,
    compute_bar6,
    compute_bar7,
    run_fixture_mode,
    run_live_mode,
)

_ROOT = Path(__file__).parent.parent.parent
FIXTURE_CLAIMS_PATH = _ROOT / "docs/eval/fixtures/sample-claims.json"
FIXTURE_RESPONSES_PATH = _ROOT / "docs/eval/fixtures/sample-analyze-responses.json"
PILOT_LABELS_PATH = _ROOT / "docs/eval/pilot-set-labels.json"


@pytest.fixture(scope="module")
def fixture_claims():
    with open(FIXTURE_CLAIMS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def fixture_responses():
    with open(FIXTURE_RESPONSES_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pilot_labels():
    with open(PILOT_LABELS_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Bar 1: ≥80% direct claims accepted-or-lightly-edited ─────────────────────

def test_bar1_computes_direct_acceptance_rate(fixture_claims):
    """Bar 1 = (direct claims with accept|edit_minor_wording) / (direct claims).

    Fixture data: claims 001 (accept), 002 (edit_minor_wording), 004 (edit_external_knowledge_override).
    Direct accepted = 001, 002 → 2/3 ≈ 0.6667. Below the 0.80 threshold (FAIL for the pilot).
    """
    result = compute_bar1(fixture_claims)
    assert result == pytest.approx(2 / 3, abs=1e-6)


def test_bar1_returns_none_when_no_direct_claims():
    claims = [{"extractionType": "interpretation", "expected_doctor_action": "accept"}]
    assert compute_bar1(claims) is None


def test_bar1_is_deterministic(fixture_claims):
    """H6: no random sampling — same input must yield same output every call."""
    assert compute_bar1(fixture_claims) == compute_bar1(fixture_claims)


def test_bar1_accept_and_edit_minor_wording_both_count():
    claims = [
        {"extractionType": "direct", "expected_doctor_action": "accept"},
        {"extractionType": "direct", "expected_doctor_action": "edit_minor_wording"},
        {"extractionType": "direct", "expected_doctor_action": "edit_correction"},
    ]
    assert compute_bar1(claims) == pytest.approx(2 / 3, abs=1e-6)


# ── Bar 2: ≥60% interpretation claims accepted ────────────────────────────────

def test_bar2_computes_interpretation_acceptance_rate(fixture_claims):
    """Fixture: claims 003 (edit_correction ✓), 005 (reject ✗) → 1/2 = 0.50.

    Below 0.60 threshold (FAIL). Computation is correct.
    """
    result = compute_bar2(fixture_claims)
    assert result == pytest.approx(1 / 2, abs=1e-6)


def test_bar2_returns_none_when_no_interpretation_claims():
    claims = [{"extractionType": "direct", "expected_doctor_action": "accept"}]
    assert compute_bar2(claims) is None


def test_bar2_reject_does_not_count_toward_numerator():
    claims = [
        {"extractionType": "interpretation", "expected_doctor_action": "reject"},
    ]
    assert compute_bar2(claims) == pytest.approx(0.0)


def test_bar2_all_four_non_reject_actions_count():
    claims = [
        {"extractionType": "interpretation", "expected_doctor_action": "accept"},
        {"extractionType": "interpretation", "expected_doctor_action": "edit_minor_wording"},
        {"extractionType": "interpretation", "expected_doctor_action": "edit_correction"},
        {"extractionType": "interpretation", "expected_doctor_action": "edit_external_knowledge_override"},
    ]
    assert compute_bar2(claims) == pytest.approx(1.0)


# ── Bar 3: ≤10% of all surfaced claims rejected ───────────────────────────────

def test_bar3_computes_rejection_rate(fixture_claims):
    """Fixture: claim 005 (reject) → 1/5 = 0.20. Above 0.10 threshold (FAIL)."""
    result = compute_bar3(fixture_claims)
    assert result == pytest.approx(1 / 5, abs=1e-6)


def test_bar3_returns_none_for_empty_claims():
    assert compute_bar3([]) is None


def test_bar3_zero_rejections():
    claims = [{"expected_doctor_action": "accept"} for _ in range(5)]
    assert compute_bar3(claims) == pytest.approx(0.0)


# ── Bar 4: 100% of claims have visible evidence span ─────────────────────────

def test_bar4_all_fixture_claims_have_evidence(fixture_claims):
    result = compute_bar4(fixture_claims)
    assert result == pytest.approx(1.0)


def test_bar4_detects_missing_evidence():
    claims = [{"extractionType": "direct", "evidence": None}]
    assert compute_bar4(claims) == pytest.approx(0.0)


def test_bar4_detects_null_evidence_text():
    claims = [{"extractionType": "direct", "evidence": {"evidenceText": None}}]
    assert compute_bar4(claims) == pytest.approx(0.0)


def test_bar4_empty_claims_vacuously_satisfied():
    assert compute_bar4([]) == pytest.approx(1.0)


# ── Bar 5: 100% of medication-change advice blocked ───────────────────────────

def test_bar5_fixture_med_blocked_claims_pass(fixture_claims):
    result = compute_bar5(fixture_claims)
    assert result == pytest.approx(1.0)


def test_bar5_vacuously_satisfied_when_no_med_claims():
    claims = [{"safetyStatus": "safe", "evidence": {"evidenceText": "x"}}]
    assert compute_bar5(claims) == pytest.approx(1.0)


def test_bar5_fails_when_blocked_claim_has_no_evidence():
    claims = [{"safetyStatus": "medicationAdviceBlocked", "evidence": None}]
    assert compute_bar5(claims) == pytest.approx(0.0)


# ── Bar 6: zero urgent-risk transcripts produce silent response ───────────────

def test_bar6_urgent_transcript_with_escalation_passes(fixture_responses, pilot_labels):
    result = compute_bar6(fixture_responses, pilot_labels)
    assert result == pytest.approx(1.0)


def test_bar6_fails_when_urgent_transcript_has_no_escalation():
    """Bar 6 must fail if an urgent transcript's fixture response has null escalationMessage.

    Self-contained: uses inline labels and responses so the test does not vacuously pass
    if pilot-set-labels.json later loses its urgent transcript.
    """
    labels = {"labels": {"t06": {"expected_urgent_claim": True, "expected_red_flag_rules": []}}}
    silent_responses = [{"inputId": "t06", "escalationMessage": None, "redFlagOnlySpans": []}]
    result = compute_bar6(silent_responses, labels)
    assert result == pytest.approx(0.0)


def test_bar6_vacuously_satisfied_with_no_urgent_transcripts():
    labels = {"labels": {"t01": {"expected_urgent_claim": False}}}
    assert compute_bar6([], labels) == pytest.approx(1.0)


# ── Bar 7: every red-flag match without urgent claim is flagged ───────────────

def test_bar7_all_red_flags_covered_in_fixture(fixture_responses, pilot_labels):
    result = compute_bar7(pilot_labels, fixture_responses)
    assert result == pytest.approx(1.0)


def test_bar7_vacuously_satisfied_with_no_red_flags():
    labels = {"labels": {"t01": {"expected_red_flag_rules": []}}}
    assert compute_bar7(labels, []) == pytest.approx(1.0)


def test_bar7_fails_when_red_flag_has_no_coverage():
    labels = {"labels": {"t06": {"expected_red_flag_rules": ["chest_pain"]}}}
    responses_without_coverage = [
        {"inputId": "t06", "escalationMessage": None, "redFlagOnlySpans": []}
    ]
    result = compute_bar7(labels, responses_without_coverage)
    assert result == pytest.approx(0.0)


def test_bar7_passes_when_red_flag_covered_by_escalation():
    labels = {"labels": {"t06": {"expected_red_flag_rules": ["chest_pain"], "expected_urgent_claim": False}}}
    responses = [{"inputId": "t06", "escalationMessage": "Please seek emergency help.", "redFlagOnlySpans": []}]
    result = compute_bar7(labels, responses)
    assert result == pytest.approx(1.0)


def test_bar7_excludes_urgent_transcripts_from_denominator():
    """Urgent transcripts belong to bar 6 scope — bar 7 must not include them."""
    labels = {"labels": {
        "t06": {"expected_red_flag_rules": ["chest_pain"], "expected_urgent_claim": True},
    }}
    result = compute_bar7(labels, [])
    assert result == pytest.approx(1.0)  # vacuous — no non-urgent red flags


# ── Live mode stub ────────────────────────────────────────────────────────────

def test_live_mode_raises_not_implemented():
    """Phase 2 must not implement --mode=live (Phase 3 work, wt-03.md step 3.5)."""
    with pytest.raises(NotImplementedError, match="Phase 3 work, see wt-03.md step 3.5"):
        run_fixture_mode(mode=EvalMode.LIVE)


# ── Result structure ──────────────────────────────────────────────────────────

def test_run_fixture_mode_returns_expected_keys():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    assert "mode" in result
    assert "zero_claim_transcripts" in result
    assert "bars" in result
    assert "all_pass" in result


def test_result_mode_is_fixture():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    assert result["mode"] == "fixture"


def test_result_has_seven_bars():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    assert len(result["bars"]) == 7


def test_result_bar_fields():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    for bar in result["bars"]:
        assert "number" in bar
        assert "name" in bar
        assert "source_field" in bar
        assert "threshold" in bar
        assert "actual" in bar
        assert "passed" in bar


# ── Zero-claim transcript handling ────────────────────────────────────────────

def test_zero_claim_transcripts_reported():
    """zero_claim_transcripts counter must be present in the result."""
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    assert isinstance(result["zero_claim_transcripts"], int)


def test_zero_claim_transcripts_is_zero_in_fixture_mode():
    """In fixture mode the fixture claims are non-zero by definition — no vacuous bars 1-3."""
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    assert result["zero_claim_transcripts"] == 0


# ── Markdown rendering ────────────────────────────────────────────────────────

def test_render_markdown_contains_mode_header():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    md = _render_markdown(result)
    assert "mode=fixture" in md


def test_render_markdown_contains_all_seven_bars():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    md = _render_markdown(result)
    for i in range(1, 8):
        assert f"| {i} |" in md


def test_render_markdown_shows_pass_or_fail():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    md = _render_markdown(result)
    assert "PASS" in md or "FAIL" in md


def test_render_markdown_reports_zero_claim_count():
    result = run_fixture_mode(mode=EvalMode.FIXTURE)
    md = _render_markdown(result)
    assert "zero_claim_transcripts" in md.lower() or "Zero-claim" in md


# ── CLI main() ────────────────────────────────────────────────────────────────

def test_main_fixture_mode_returns_nonzero_when_bars_fail():
    """With current fixture data, bars 1/2/3 are below threshold — exit code = 1."""
    from run_eval import main
    exit_code = main(["--mode", "fixture"])
    assert exit_code == 1  # not all bars pass in fixture mode


def test_main_writes_json_output_file(tmp_path):
    from run_eval import main
    out = tmp_path / "eval-out.json"
    main(["--mode", "fixture", "--out", str(out)])
    assert out.exists()
    data = json.loads(out.read_text())
    assert "bars" in data
    assert "mode" in data
    assert data["mode"] == "fixture"


# ── Live-mode bar 1: doctorReviewStatus + extractionType=direct ───────────────

def test_bar1_live_excludes_pending_claims_from_cohort():
    """Pending claims must not count in numerator OR denominator."""
    claims = [
        {"extractionType": "direct", "doctorReviewStatus": "accepted"},
        {"extractionType": "direct", "doctorReviewStatus": "pending"},
        {"extractionType": "direct", "doctorReviewStatus": "rejected"},
    ]
    # cohort = 2 reviewed (1 accepted, 1 rejected) → 0.5
    assert compute_bar1_live(claims) == pytest.approx(0.5)


def test_bar1_live_returns_none_when_all_pending():
    """All-pending direct cohort = vacuous → None (informational PASS in live)."""
    claims = [
        {"extractionType": "direct", "doctorReviewStatus": "pending"},
        {"extractionType": "direct", "doctorReviewStatus": "pending"},
    ]
    assert compute_bar1_live(claims) is None


def test_bar1_live_returns_none_when_no_direct_claims():
    claims = [{"extractionType": "interpretation", "doctorReviewStatus": "accepted"}]
    assert compute_bar1_live(claims) is None


def test_bar1_live_minor_wording_edit_counts_as_acceptance():
    claims = [
        {"extractionType": "direct", "doctorReviewStatus": "edited",
         "doctorEditOrigin": "minor_wording"},
        {"extractionType": "direct", "doctorReviewStatus": "edited",
         "doctorEditOrigin": "correction"},
    ]
    # 1 of 2 reviewed counts as accepted → 0.5
    assert compute_bar1_live(claims) == pytest.approx(0.5)


def test_bar1_live_external_knowledge_override_does_not_count():
    """external_knowledge_override is a substantive correction, not 'lightly edited'."""
    claims = [
        {"extractionType": "direct", "doctorReviewStatus": "edited",
         "doctorEditOrigin": "external_knowledge_override"},
    ]
    assert compute_bar1_live(claims) == pytest.approx(0.0)


# ── Live-mode bar 2: doctorReviewStatus + extractionType=interpretation ───────

def test_bar2_live_non_rejected_count_as_accepted():
    """Any reviewed interpretation claim that isn't 'rejected' counts."""
    claims = [
        {"extractionType": "interpretation", "doctorReviewStatus": "accepted"},
        {"extractionType": "interpretation", "doctorReviewStatus": "edited",
         "doctorEditOrigin": "external_knowledge_override"},
        {"extractionType": "interpretation", "doctorReviewStatus": "rejected"},
    ]
    # 2 of 3 reviewed → 0.6667
    assert compute_bar2_live(claims) == pytest.approx(2 / 3)


def test_bar2_live_returns_none_when_all_pending():
    claims = [{"extractionType": "interpretation", "doctorReviewStatus": "pending"}]
    assert compute_bar2_live(claims) is None


def test_bar2_live_returns_none_when_no_interpretation_claims():
    claims = [{"extractionType": "direct", "doctorReviewStatus": "accepted"}]
    assert compute_bar2_live(claims) is None


# ── Live-mode bar 3: rejection rate across all reviewed claims ────────────────

def test_bar3_live_excludes_pending():
    claims = [
        {"doctorReviewStatus": "accepted"},
        {"doctorReviewStatus": "pending"},
        {"doctorReviewStatus": "rejected"},
        {"doctorReviewStatus": "edited", "doctorEditOrigin": "minor_wording"},
    ]
    # cohort = 3 reviewed (1 accepted, 1 rejected, 1 edited) → 1/3
    assert compute_bar3_live(claims) == pytest.approx(1 / 3)


def test_bar3_live_returns_none_when_all_pending():
    claims = [{"doctorReviewStatus": "pending"}, {"doctorReviewStatus": "pending"}]
    assert compute_bar3_live(claims) is None


def test_bar3_live_zero_rejections_returns_zero():
    claims = [
        {"doctorReviewStatus": "accepted"},
        {"doctorReviewStatus": "accepted"},
    ]
    assert compute_bar3_live(claims) == pytest.approx(0.0)


# ── _render_live_header: required keys + valid JSON ───────────────────────────

def test_render_live_header_produces_valid_json_with_required_keys():
    result = {
        "mode": "live",
        "prompt_version_hash": "abc123",
        "model_id": "claude-sonnet-4-6",
        "dataset_size": 10,
        "timestamp_utc": "2026-04-29T12:34:56Z",
    }
    rendered = _render_live_header(result)
    parsed = json.loads(rendered)
    assert parsed["mode"] == "live"
    assert parsed["prompt_version_hash"] == "abc123"
    assert parsed["model_id"] == "claude-sonnet-4-6"
    assert parsed["dataset_size"] == 10
    assert parsed["timestamp_utc"] == "2026-04-29T12:34:56Z"


def test_render_live_header_handles_missing_optional_keys():
    """Header must still be emittable when prompt_version_hash/model_id are blank."""
    result = {"mode": "live"}
    rendered = _render_live_header(result)
    parsed = json.loads(rendered)
    assert parsed["mode"] == "live"
    assert parsed["prompt_version_hash"] == ""
    assert parsed["model_id"] == ""
    assert parsed["dataset_size"] == 0


# ── run_live_mode orchestrator: httpx.MockTransport (in-process; no server) ──

def _build_mock_response(transcript_id: str, *, escalation: bool = False,
                        claims: list[dict] | None = None) -> dict:
    """Mimic the AnalyzeResponse shape returned by /analyze/cached."""
    return {
        "inputId": transcript_id,
        "promptVersionHash": "hash-test-001",
        "modelId": "claude-sonnet-4-6",
        "claims": claims or [],
        "escalationMessage": "Please seek emergency help." if escalation else None,
        "redFlagOnlySpans": (
            [{"startChar": 0, "endChar": 5, "ruleKey": "chest_pain"}]
            if escalation else []
        ),
        "createdAt": "2026-04-29T12:00:00+00:00",
    }


def _make_mock_transport(responses_by_id: dict[str, dict]) -> httpx.MockTransport:
    """Mock /precompute (always 200) + /analyze/cached/{id} (lookup by id)."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/precompute":
            return httpx.Response(
                200,
                json={"cached": 0, "refreshed": len(responses_by_id),
                      "total": len(responses_by_id)},
            )
        if request.method == "GET" and request.url.path.startswith("/analyze/cached/"):
            tid = request.url.path.rsplit("/", 1)[-1]
            if tid in responses_by_id:
                return httpx.Response(200, json=responses_by_id[tid])
            return httpx.Response(404, json={"detail": "Not found"})
        return httpx.Response(500, json={"detail": "unexpected"})
    return httpx.MockTransport(handler)


@pytest.fixture
def fake_pilot_set(tmp_path: Path) -> Path:
    """Tiny pilot-set.json with two transcripts (one urgent, one non-urgent)."""
    data = {
        "version": "1",
        "transcripts": [
            {
                "id": "tA",
                "patientId": "pA",
                "rawText": "Severe breathing difficulty.",
                "context": {},
                "edge_cases": ["urgent_red_flag"],
            },
            {
                "id": "tB",
                "patientId": "pB",
                "rawText": "Mild stomach upset.",
                "context": {},
                "edge_cases": ["vague"],
            },
        ],
    }
    out = tmp_path / "pilot-set.json"
    out.write_text(json.dumps(data))
    return out


@pytest.fixture
def fake_pilot_labels(tmp_path: Path) -> Path:
    """Labels matching the fake_pilot_set transcripts."""
    data = {
        "version": "1",
        "labels": {
            "tA": {
                "expected_urgent_claim": True,
                "expected_red_flag_rules": ["severe_breathing_difficulty"],
            },
            "tB": {
                "expected_urgent_claim": False,
                "expected_red_flag_rules": [],
            },
        },
    }
    out = tmp_path / "pilot-set-labels.json"
    out.write_text(json.dumps(data))
    return out


def test_run_live_mode_emits_header_fields(fake_pilot_set, fake_pilot_labels):
    transport = _make_mock_transport({
        "tA": _build_mock_response("tA", escalation=True),
        "tB": _build_mock_response("tB", escalation=False),
    })
    with httpx.Client(transport=transport, base_url="http://test") as client:
        result = run_live_mode(
            host="http://test",
            pilot_set_path=fake_pilot_set,
            pilot_labels_path=fake_pilot_labels,
            http_client=client,
        )
    assert result["mode"] == "live"
    assert result["prompt_version_hash"] == "hash-test-001"
    assert result["model_id"] == "claude-sonnet-4-6"
    assert result["dataset_size"] == 2
    assert "timestamp_utc" in result
    assert result["host"] == "http://test"


def test_run_live_mode_zero_claim_transcripts_counted(fake_pilot_set, fake_pilot_labels):
    """Both transcripts return zero claims → zero_claim_transcripts == 2."""
    transport = _make_mock_transport({
        "tA": _build_mock_response("tA", escalation=True),
        "tB": _build_mock_response("tB", escalation=False),
    })
    with httpx.Client(transport=transport, base_url="http://test") as client:
        result = run_live_mode(
            host="http://test",
            pilot_set_path=fake_pilot_set,
            pilot_labels_path=fake_pilot_labels,
            http_client=client,
        )
    assert result["zero_claim_transcripts"] == 2


def test_run_live_mode_bars_1_3_pass_when_all_pending(
    fake_pilot_set, fake_pilot_labels
):
    """All claims pending → bars 1-3 vacuous → PASS informationally."""
    pending_claim = {
        "claimId": "11111111-1111-1111-1111-111111111111",
        "extractionType": "direct",
        "doctorReviewStatus": "pending",
        "evidence": {"evidenceText": "severe breathing"},
        "safetyStatus": "safe",
    }
    transport = _make_mock_transport({
        "tA": _build_mock_response("tA", escalation=True, claims=[pending_claim]),
        "tB": _build_mock_response("tB", escalation=False),
    })
    with httpx.Client(transport=transport, base_url="http://test") as client:
        result = run_live_mode(
            host="http://test",
            pilot_set_path=fake_pilot_set,
            pilot_labels_path=fake_pilot_labels,
            http_client=client,
        )
    bars_by_num = {b["number"]: b for b in result["bars"]}
    # bars 1-3 are vacuous (all-pending) → actual=None, passed=True
    assert bars_by_num[1]["actual"] is None
    assert bars_by_num[1]["passed"] is True
    assert bars_by_num[2]["actual"] is None
    assert bars_by_num[2]["passed"] is True
    assert bars_by_num[3]["actual"] is None
    assert bars_by_num[3]["passed"] is True


def test_run_live_mode_bar6_passes_when_urgent_transcript_has_escalation(
    fake_pilot_set, fake_pilot_labels
):
    transport = _make_mock_transport({
        "tA": _build_mock_response("tA", escalation=True),
        "tB": _build_mock_response("tB", escalation=False),
    })
    with httpx.Client(transport=transport, base_url="http://test") as client:
        result = run_live_mode(
            host="http://test",
            pilot_set_path=fake_pilot_set,
            pilot_labels_path=fake_pilot_labels,
            http_client=client,
        )
    bars_by_num = {b["number"]: b for b in result["bars"]}
    assert bars_by_num[6]["passed"] is True
    assert bars_by_num[6]["actual"] == 1.0


def test_run_live_mode_bar6_fails_when_urgent_transcript_silent(
    fake_pilot_set, fake_pilot_labels
):
    """Urgent label but null escalationMessage → bar 6 must FAIL (sticky broken)."""
    transport = _make_mock_transport({
        "tA": _build_mock_response("tA", escalation=False),  # SILENT — bug
        "tB": _build_mock_response("tB", escalation=False),
    })
    with httpx.Client(transport=transport, base_url="http://test") as client:
        result = run_live_mode(
            host="http://test",
            pilot_set_path=fake_pilot_set,
            pilot_labels_path=fake_pilot_labels,
            http_client=client,
        )
    bars_by_num = {b["number"]: b for b in result["bars"]}
    assert bars_by_num[6]["passed"] is False
    assert result["all_pass"] is False


def test_run_live_mode_raises_on_malformed_pilot_set(tmp_path, fake_pilot_labels):
    """Invalid pilot-set.json (no 'transcripts' key) must raise — fail loud."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"version": "1"}))
    with pytest.raises(ValueError, match="missing 'transcripts'"):
        run_live_mode(
            host="http://test",
            pilot_set_path=bad,
            pilot_labels_path=fake_pilot_labels,
            http_client=httpx.Client(transport=_make_mock_transport({})),
        )


def test_run_live_mode_propagates_precompute_failure(
    fake_pilot_set, fake_pilot_labels
):
    """Server returning 500 on /precompute must surface as HTTPStatusError."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/precompute":
            return httpx.Response(500, json={"detail": "boom"})
        return httpx.Response(404)
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        with pytest.raises(httpx.HTTPStatusError):
            run_live_mode(
                host="http://test",
                pilot_set_path=fake_pilot_set,
                pilot_labels_path=fake_pilot_labels,
                http_client=client,
            )
