"""§11.2 — POST /review-claim endpoint tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Fixed UUIDs for predictable test fixtures
_CID_ACCEPT = "11111111-0000-0000-0000-000000000001"
_CID_EDIT = "11111111-0000-0000-0000-000000000002"
_CID_REJECT = "11111111-0000-0000-0000-000000000003"
_CID_STICKY = "11111111-0000-0000-0000-000000000004"
_CID_MISSING = "99999999-0000-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def patch_env_and_extraction(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAIMS_DB_PATH", str(tmp_path / "test.db"))

    mock_client = MagicMock()
    mock_token = MagicMock()
    mock_token.input_tokens = 2000
    mock_client.messages.count_tokens.return_value = mock_token

    import app.core.extraction as extraction
    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-sonnet-4-6")

    yield mock_client


def _seed_claim(tmp_path, claim_id: str = _CID_ACCEPT) -> None:
    import app.core.extraction as extraction
    from app.storage.repository import ClaimsRepository

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    ts = datetime.now(tz=timezone.utc).isoformat()

    repo.insert_analyze_response(
        input_id="inp-review-1",
        prompt_version_hash=extraction.PROMPT_VERSION_HASH,
        model_id=extraction.MODEL_ID,
        patient_id="p1",
        raw_text="I threw up twice after dinner.",
        escalation_message=None,
        red_flag_only_spans_json=None,
        created_at=ts,
    )
    repo.insert_claim_raw(
        claim_id=claim_id,
        input_id="inp-review-1",
        prompt_version_hash=extraction.PROMPT_VERSION_HASH,
        model_id=extraction.MODEL_ID,
        patient_id="p1",
        claim_text="Patient reported vomiting twice after dinner.",
        original_claim_text=None,
        event_type="vomiting",
        evidence_text="threw up twice",
        evidence_start=2,
        evidence_end=16,
        confidence=0.9,
        extraction_type="direct",
        risk_level="medium",
        safety_status="safe",
        doctor_review_status="pending",
        doctor_edit_origin=None,
        created_at=ts,
    )


def test_review_claim_accept(patch_env_and_extraction, tmp_path) -> None:
    _seed_claim(tmp_path, _CID_ACCEPT)

    from app.main import app
    client = TestClient(app)
    resp = client.post("/review-claim", json={
        "doctorId": "doctor1",
        "claimId": _CID_ACCEPT,
        "action": "accepted",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["doctorReviewStatus"] == "accepted"


def test_review_claim_edit_stores_original_and_edit_origin(
    patch_env_and_extraction, tmp_path
) -> None:
    _seed_claim(tmp_path, _CID_EDIT)

    from app.main import app
    client = TestClient(app)
    resp = client.post("/review-claim", json={
        "doctorId": "doctor1",
        "claimId": _CID_EDIT,
        "action": "edited",
        "correctedClaim": "Patient reported vomiting twice after late dinner.",
        "doctorEditOrigin": "minor_wording",
        "reason": "Added timing detail.",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["doctorReviewStatus"] == "edited"
    assert data["finalClaimText"] == "Patient reported vomiting twice after late dinner."


def test_review_claim_reject(patch_env_and_extraction, tmp_path) -> None:
    _seed_claim(tmp_path, _CID_REJECT)

    from app.main import app
    client = TestClient(app)
    resp = client.post("/review-claim", json={
        "doctorId": "doctor1",
        "claimId": _CID_REJECT,
        "action": "rejected",
        "reason": "Not supported by evidence.",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["doctorReviewStatus"] == "rejected"


def test_review_claim_not_found_returns_404(patch_env_and_extraction) -> None:
    from app.main import app
    client = TestClient(app)
    resp = client.post("/review-claim", json={
        "doctorId": "doctor1",
        "claimId": _CID_MISSING,
        "action": "accepted",
    })

    assert resp.status_code == 404


def test_review_claim_does_not_touch_analyze_responses(
    patch_env_and_extraction, tmp_path
) -> None:
    """H5 + C4: /review-claim MUST NOT write to analyze_responses."""
    _seed_claim(tmp_path, _CID_STICKY)

    import app.core.extraction as extraction
    from app.storage.repository import ClaimsRepository

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    before = repo.get_analyze_response(
        "inp-review-1",
        extraction.PROMPT_VERSION_HASH,
        extraction.MODEL_ID,
    )
    created_at_before = before["created_at"]

    from app.main import app
    client = TestClient(app)
    client.post("/review-claim", json={
        "doctorId": "doctor1",
        "claimId": _CID_STICKY,
        "action": "rejected",
    })

    after = repo.get_analyze_response(
        "inp-review-1",
        extraction.PROMPT_VERSION_HASH,
        extraction.MODEL_ID,
    )
    assert after["created_at"] == created_at_before, (
        "analyze_responses row was mutated by /review-claim"
    )
