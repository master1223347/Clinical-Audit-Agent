"""C4 — Zero-claim escalation persistence test (wt-01.md required test #5)."""

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


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


def _stub_llm_empty(mock_client) -> None:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock()]
    mock_msg.content[0].text = json.dumps([])  # LLM returns zero claims
    mock_msg.usage.cache_read_input_tokens = 0
    mock_msg.usage.input_tokens = 100
    mock_client.messages.create.return_value = mock_msg


def test_zero_claim_urgent_transcript_still_has_analyze_response_row(
    patch_env_and_extraction, tmp_path
) -> None:
    """C4: zero-claim transcript writes one analyze_responses row."""
    mock_client = patch_env_and_extraction
    _stub_llm_empty(mock_client)

    # Use a raw text that triggers urgent red flags even with zero LLM claims
    raw_text = "I have severe chest pain right now."

    from app.main import app
    client = TestClient(app)
    resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": raw_text,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["claims"] == []

    import app.core.extraction as extraction
    from app.storage.repository import ClaimsRepository

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    row = repo.get_analyze_response(
        data["inputId"], extraction.PROMPT_VERSION_HASH, extraction.MODEL_ID
    )
    assert row is not None, "analyze_responses must have a row even when claims=[]"


def test_cached_endpoint_returns_200_with_empty_claims_not_404(
    patch_env_and_extraction, tmp_path
) -> None:
    """C4: GET /analyze/cached/{id} returns 200+claims=[] for zero-claim, not 404."""
    mock_client = patch_env_and_extraction
    _stub_llm_empty(mock_client)

    raw_text = "I had severe chest pain this morning."
    from app.main import app
    client = TestClient(app)

    analyze_resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": raw_text,
    })
    assert analyze_resp.status_code == 200
    input_id = analyze_resp.json()["inputId"]

    cached_resp = client.get(f"/analyze/cached/{input_id}")
    assert cached_resp.status_code == 200, (
        f"Expected 200 for zero-claim cached response, got {cached_resp.status_code}"
    )
    cached_data = cached_resp.json()
    assert cached_data["claims"] == []


def test_zero_claim_urgent_has_escalation_message(
    patch_env_and_extraction, tmp_path
) -> None:
    """C4 + §13.4: zero-claim urgent transcript still has escalation_message on response row."""
    mock_client = patch_env_and_extraction
    _stub_llm_empty(mock_client)

    raw_text = "I have severe chest pain. I think I am having a heart attack."
    from app.main import app
    client = TestClient(app)

    resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": raw_text,
    })

    assert resp.status_code == 200
    data = resp.json()
    # Rule-based red-flag detection should still produce escalation even with zero LLM claims
    # (chest pain is an urgent red flag)
    import app.core.extraction as extraction
    from app.storage.repository import ClaimsRepository

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    row = repo.get_analyze_response(
        data["inputId"], extraction.PROMPT_VERSION_HASH, extraction.MODEL_ID
    )
    assert row["escalation_message"] is not None, (
        "Urgent red-flag text must produce escalation_message even with zero claims"
    )
