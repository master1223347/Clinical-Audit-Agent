"""Phase 3b sticky-escalation regression against the live wt-01 backend.

Per pilot.md §2 and wt-01.md C4, ``analyze_responses`` is structurally
immutable. ``/review-claim`` only mutates rows in the ``claims`` table; there
is no code path from a doctor action to a response-level field. After a
doctor rejects or edits an urgent claim, the cached response payload's
``escalationMessage``, ``redFlagOnlySpans`` and ``createdAt`` MUST be
byte-identical to the original ``/analyze/cached`` result.

This test hits a real wt-01 server on ``localhost:8000``. It does NOT mock
the server. When the health probe fails the test is skipped cleanly so
fixture-mode CI runs are not broken.

Run it via:

    pytest tests/eval/test_sticky_escalation_live.py -v

Override the host with ``EVAL_LIVE_HOST`` if needed.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx
import pytest

_REPO_ROOT = Path(__file__).parent.parent.parent
PILOT_SET_PATH = _REPO_ROOT / "docs/eval/pilot-set.json"

LIVE_HOST: str = os.environ.get("EVAL_LIVE_HOST", "http://localhost:8000")
HEALTH_TIMEOUT_S: float = 5.0
LIVE_TIMEOUT_S: float = 60.0
URGENT_TRANSCRIPT_ID: str = "t06"


def _server_up(host: str) -> bool:
    """Return True iff ``GET {host}/health`` returns 200 within the timeout."""
    try:
        r = httpx.get(f"{host}/health", timeout=HEALTH_TIMEOUT_S)
        return r.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


@pytest.fixture(scope="module")
def live_host() -> str:
    if not _server_up(LIVE_HOST):
        pytest.skip(f"live wt-01 server not reachable at {LIVE_HOST}/health")
    return LIVE_HOST


@pytest.fixture(scope="module")
def http_client(live_host: str):
    with httpx.Client(base_url=live_host, timeout=LIVE_TIMEOUT_S) as client:
        yield client


def _canon(value: object) -> str:
    """Stable JSON serialization for byte-identity comparison.

    Uses sorted keys and tight separators so we catch whitespace and
    key-order regressions on dicts. Comparing parsed dicts via ``==``
    silently normalizes both — that is exactly what this helper avoids.

    Note: list element ORDER is preserved (json.dumps does not sort lists).
    The escalation triple's only list field — ``redFlagOnlySpans`` — uses
    :func:`_canon_spans` instead so semantically-equivalent reorderings of
    rule matches do NOT trip the assertion as a false positive.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _canon_spans(spans: object) -> str:
    """Order-insensitive canonical form for ``redFlagOnlySpans``.

    Each span dict is canonicalised individually then the list is sorted
    by canonical string. Catches content/key regressions on each span but
    is robust to a server-side reorder of semantically-equivalent matches
    (per python-reviewer MEDIUM #2).
    """
    if spans is None:
        return _canon(None)
    if not isinstance(spans, list):
        return _canon(spans)
    item_canons = sorted(_canon(item) for item in spans)
    return "[" + ",".join(item_canons) + "]"


def _load_urgent_transcript() -> dict:
    with open(PILOT_SET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for transcript in data["transcripts"]:
        if transcript["id"] == URGENT_TRANSCRIPT_ID:
            return transcript
    raise RuntimeError(
        f"transcript {URGENT_TRANSCRIPT_ID} missing from {PILOT_SET_PATH}"
    )


def _precompute_urgent(client: httpx.Client) -> None:
    transcript = _load_urgent_transcript()
    items = [
        {
            "transcript_id": transcript["id"],
            "raw_text": transcript["rawText"],
            "patient_id": transcript["patientId"],
            "context": transcript.get("context", {}),
        }
    ]
    response = client.post("/precompute", json=items)
    assert response.status_code == 200, (
        f"/precompute failed for {URGENT_TRANSCRIPT_ID}: "
        f"{response.status_code} {response.text}"
    )


def _get_cached(client: httpx.Client, transcript_id: str) -> dict:
    response = client.get(f"/analyze/cached/{transcript_id}")
    assert response.status_code == 200, (
        f"/analyze/cached/{transcript_id} failed: "
        f"{response.status_code} {response.text}"
    )
    return response.json()


def _escalation_signature(payload: dict) -> tuple[str, str, str | None]:
    """Tuple of canonical-JSON strings for the three sticky-escalation fields.

    ``createdAt`` is compared as a raw string so a server-side re-emit of
    the row (which would change the timestamp) is caught directly.
    ``redFlagOnlySpans`` uses an order-insensitive canon (see
    :func:`_canon_spans`) so the test catches content regressions but is
    robust to span reordering.
    """
    return (
        _canon(payload.get("escalationMessage")),
        _canon_spans(payload.get("redFlagOnlySpans")),
        payload.get("createdAt"),
    )


def _post_review(
    client: httpx.Client,
    *,
    claim_id: str,
    action: str,
    corrected_claim: str | None = None,
    doctor_edit_origin: str | None = None,
    reason: str | None = None,
) -> None:
    body: dict[str, object] = {
        "doctorId": f"sticky-test-{uuid.uuid4()}",
        "claimId": claim_id,
        "action": action,
    }
    if corrected_claim is not None:
        body["correctedClaim"] = corrected_claim
    if doctor_edit_origin is not None:
        body["doctorEditOrigin"] = doctor_edit_origin
    if reason is not None:
        body["reason"] = reason
    response = client.post("/review-claim", json=body)
    assert response.status_code == 200, (
        f"/review-claim {action} failed: {response.status_code} {response.text}"
    )


def test_escalation_fields_byte_identical_across_claim_mutations(
    http_client: httpx.Client,
) -> None:
    """After reject + edit-downgrade, the response-level escalation triple
    is byte-identical to the original ``/analyze/cached`` result.

    Reads ``escalationMessage`` + ``redFlagOnlySpans`` + ``createdAt`` from
    the cached payload, hashes each via ``_canon``, and compares the triples.
    """
    _precompute_urgent(http_client)

    baseline = _get_cached(http_client, URGENT_TRANSCRIPT_ID)

    if not baseline.get("claims"):
        pytest.skip(
            f"transcript {URGENT_TRANSCRIPT_ID} returned zero claims; "
            "sticky-mutation test requires at least one claim to mutate"
        )

    baseline_signature = _escalation_signature(baseline)

    assert baseline_signature[0] != _canon(None), (
        f"transcript {URGENT_TRANSCRIPT_ID} expected to surface a non-null "
        "escalationMessage; got null. Re-check pilot-set-labels.json or "
        "app/rules/red_flag_rules.py."
    )

    first_claim_id: str = baseline["claims"][0]["claimId"]

    _post_review(
        http_client,
        claim_id=first_claim_id,
        action="rejected",
        reason="sticky-escalation regression test",
    )

    after_reject = _get_cached(http_client, URGENT_TRANSCRIPT_ID)
    after_reject_signature = _escalation_signature(after_reject)

    assert after_reject_signature == baseline_signature, (
        "sticky-escalation broken after REJECT — "
        f"baseline={baseline_signature} after={after_reject_signature}"
    )

    second_claim_id: str = (
        baseline["claims"][1]["claimId"]
        if len(baseline["claims"]) > 1
        else first_claim_id
    )

    _post_review(
        http_client,
        claim_id=second_claim_id,
        action="edited",
        corrected_claim=(
            "Patient reports lightheadedness (downgraded from fainting "
            "by Phase 3b sticky regression test)."
        ),
        doctor_edit_origin="external_knowledge_override",
    )

    after_edit = _get_cached(http_client, URGENT_TRANSCRIPT_ID)
    after_edit_signature = _escalation_signature(after_edit)

    assert after_edit_signature == baseline_signature, (
        "sticky-escalation broken after EDIT-downgrade — "
        f"baseline={baseline_signature} after={after_edit_signature}"
    )
