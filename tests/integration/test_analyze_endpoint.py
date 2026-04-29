"""§11.1 — POST /analyze endpoint integration tests."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import (
    SAMPLE_SAFE_TRANSCRIPT,
    SAMPLE_URGENT_TRANSCRIPT,
    SAMPLE_ZERO_CLAIM_URGENT_TRANSCRIPT,
)


def _make_extraction_response(claims: list[dict]) -> str:
    return json.dumps(claims)


@pytest.fixture(autouse=True)
def patch_extraction_and_db(tmp_path, monkeypatch):
    """Patch Anthropic client and DB path for all integration tests."""
    monkeypatch.setenv("CLAIMS_DB_PATH", str(tmp_path / "test.db"))

    mock_client = MagicMock()
    mock_token = MagicMock()
    mock_token.input_tokens = 2000
    mock_client.messages.count_tokens.return_value = mock_token

    import app.core.extraction as extraction
    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-sonnet-4-6")

    yield mock_client


def _stub_llm_response(mock_client, claims_json: list[dict]) -> None:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock()]
    mock_msg.content[0].text = json.dumps(claims_json)
    mock_msg.usage.cache_read_input_tokens = 0
    mock_msg.usage.input_tokens = 100
    mock_client.messages.create.return_value = mock_msg


def test_health_check(patch_extraction_and_db) -> None:
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_analyze_returns_200_with_claims(patch_extraction_and_db, tmp_path) -> None:
    mock_client = patch_extraction_and_db
    _stub_llm_response(mock_client, [
        {
            "claimText": "Patient reported vomiting twice after dinner.",
            "eventType": "vomiting",
            "evidenceText": "threw up twice",
            "confidence": 0.95,
            "extractionType": "direct",
            "missingInfo": ["blood in vomit"],
            "riskLevel": "medium",
            "safetyStatus": "safe",
        }
    ])

    raw_text = "I threw up twice after dinner."
    from app.main import app
    client = TestClient(app)
    resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": raw_text,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert "inputId" in data
    assert "claims" in data


def test_analyze_writes_analyze_responses_row(patch_extraction_and_db, tmp_path) -> None:
    mock_client = patch_extraction_and_db
    _stub_llm_response(mock_client, [])  # zero claims

    import os
    os.environ["CLAIMS_DB_PATH"] = str(tmp_path / "test.db")

    from app.main import app
    from app.storage.repository import ClaimsRepository

    client = TestClient(app)
    resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": "I had a mild headache.",
    })

    assert resp.status_code == 200
    data = resp.json()
    input_id = data["inputId"]

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    import app.core.extraction as extraction
    row = repo.get_analyze_response(
        input_id, extraction.PROMPT_VERSION_HASH, extraction.MODEL_ID
    )
    assert row is not None


def test_analyze_urgent_produces_escalation_message(patch_extraction_and_db, tmp_path) -> None:
    """§13.4: urgent-risk transcript produces escalation_message."""
    mock_client = patch_extraction_and_db
    _stub_llm_response(mock_client, [
        {
            "claimText": "Patient reported blood in vomit and fainting.",
            "eventType": "vomiting",
            "evidenceText": "blood in my vomit and I fainted",
            "confidence": 0.97,
            "extractionType": "direct",
            "missingInfo": [],
            "riskLevel": "urgent",
            "safetyStatus": "safe",
        }
    ])

    raw_text = "I had blood in my vomit and I fainted briefly."
    from app.main import app
    client = TestClient(app)
    resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": raw_text,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("escalationMessage") is not None
    assert len(data["escalationMessage"]) > 0


def test_analyze_zero_claims_still_returns_200(patch_extraction_and_db) -> None:
    mock_client = patch_extraction_and_db
    _stub_llm_response(mock_client, [])

    from app.main import app
    client = TestClient(app)
    resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": "I felt fine today.",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["claims"] == []
