"""Precompute pipeline tests — pilot.md C3, C4, 2.11."""

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


def _stub_llm(mock_client, claims_json: list[dict]) -> None:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock()]
    mock_msg.content[0].text = json.dumps(claims_json)
    mock_msg.usage.cache_read_input_tokens = 0
    mock_msg.usage.input_tokens = 100
    mock_client.messages.create.return_value = mock_msg


def test_precompute_populates_cache(patch_env_and_extraction, tmp_path) -> None:
    mock_client = patch_env_and_extraction
    _stub_llm(mock_client, [
        {
            "claimText": "Patient reported vomiting.",
            "eventType": "vomiting",
            "evidenceText": "threw up",
            "confidence": 0.9,
            "extractionType": "direct",
            "missingInfo": [],
            "riskLevel": "medium",
            "safetyStatus": "safe",
        }
    ])

    from app.main import app
    client = TestClient(app)
    resp = client.post("/precompute", json=[
        {"transcript_id": "t1", "raw_text": "I threw up twice.", "patient_id": "p1"}
    ])
    assert resp.status_code == 200

    cached_resp = client.get("/analyze/cached/t1")
    assert cached_resp.status_code == 200
    data = cached_resp.json()
    assert data["claims"]


def test_precompute_idempotent(patch_env_and_extraction) -> None:
    mock_client = patch_env_and_extraction
    _stub_llm(mock_client, [])

    from app.main import app
    client = TestClient(app)

    # Run twice
    client.post("/precompute", json=[
        {"transcript_id": "t2", "raw_text": "Mild headache.", "patient_id": "p1"}
    ])
    resp2 = client.post("/precompute", json=[
        {"transcript_id": "t2", "raw_text": "Mild headache.", "patient_id": "p1"}
    ])
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["cached"] == 1  # second run is a cache hit
    assert data["refreshed"] == 0


def test_get_cached_returns_404_when_never_computed(patch_env_and_extraction) -> None:
    from app.main import app
    client = TestClient(app)
    resp = client.get("/analyze/cached/never-seen-transcript")
    assert resp.status_code == 404


def test_precompute_zero_claim_transcript_still_200(patch_env_and_extraction) -> None:
    mock_client = patch_env_and_extraction
    _stub_llm(mock_client, [])

    from app.main import app
    client = TestClient(app)
    client.post("/precompute", json=[
        {"transcript_id": "t3", "raw_text": "I feel fine.", "patient_id": "p1"}
    ])

    cached_resp = client.get("/analyze/cached/t3")
    assert cached_resp.status_code == 200
    data = cached_resp.json()
    assert data["claims"] == []


def test_prompt_version_change_causes_cache_miss(
    patch_env_and_extraction, tmp_path, monkeypatch
) -> None:
    """C3: changing PROMPT_VERSION_HASH → GET /analyze/cached returns 404."""
    mock_client = patch_env_and_extraction
    _stub_llm(mock_client, [])

    from app.main import app
    client = TestClient(app)
    client.post("/precompute", json=[
        {"transcript_id": "t4", "raw_text": "I feel fine.", "patient_id": "p1"}
    ])

    # Verify it was cached
    resp = client.get("/analyze/cached/t4")
    assert resp.status_code == 200

    # Simulate prompt change by modifying PROMPT_VERSION_HASH
    import app.core.extraction as extraction
    monkeypatch.setattr(extraction, "PROMPT_VERSION_HASH", "new-hash-after-prompt-change")

    # Now the cache lookup should miss (different hash)
    resp_after = client.get("/analyze/cached/t4")
    assert resp_after.status_code == 404
