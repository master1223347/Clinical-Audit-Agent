"""M6 — make precompute-fresh destructive test (wt-01.md required test #8)."""

import json
import subprocess
import sys
from datetime import datetime, timezone
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


def _stub_llm(mock_client) -> None:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock()]
    mock_msg.content[0].text = json.dumps([
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
    mock_msg.usage.cache_read_input_tokens = 0
    mock_msg.usage.input_tokens = 100
    mock_client.messages.create.return_value = mock_msg


def test_truncate_all_removes_both_tables(patch_env_and_extraction, tmp_path) -> None:
    """M6: truncate both tables; manual click state is gone."""
    mock_client = patch_env_and_extraction
    _stub_llm(mock_client)

    from app.main import app
    from app.storage.repository import ClaimsRepository
    import app.core.extraction as extraction

    client = TestClient(app)

    # Populate via analyze
    resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": "I threw up twice.",
    })
    assert resp.status_code == 200
    data = resp.json()
    input_id = data["inputId"]

    # Simulate doctor click (accept the claim)
    if data["claims"]:
        claim_id = data["claims"][0]["claimId"]
        client.post("/review-claim", json={
            "doctorId": "doctor1",
            "claimId": claim_id,
            "action": "accepted",
        })

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    # Verify data exists before truncation
    row_before = repo.get_analyze_response(
        input_id, extraction.PROMPT_VERSION_HASH, extraction.MODEL_ID
    )
    assert row_before is not None

    # Truncate
    repo.truncate_all()

    # Both tables empty
    row_after = repo.get_analyze_response(
        input_id, extraction.PROMPT_VERSION_HASH, extraction.MODEL_ID
    )
    assert row_after is None, "analyze_responses should be empty after truncate_all"

    claims_after = repo.list_claims_for_response(
        input_id, extraction.PROMPT_VERSION_HASH, extraction.MODEL_ID
    )
    assert claims_after == [], "claims should be empty after truncate_all"
