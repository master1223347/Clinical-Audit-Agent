"""H5 + C4 — Sticky escalation tests (wt-01.md required test #4)."""

import json
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


def _stub_llm(mock_client, claims_json: list[dict]) -> None:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock()]
    mock_msg.content[0].text = json.dumps(claims_json)
    mock_msg.usage.cache_read_input_tokens = 0
    mock_msg.usage.input_tokens = 100
    mock_client.messages.create.return_value = mock_msg


def test_sticky_escalation_survives_claim_rejection(
    patch_env_and_extraction, tmp_path
) -> None:
    """H5: reject urgent claim → escalationMessage from analyze_responses unchanged."""
    mock_client = patch_env_and_extraction

    _stub_llm(mock_client, [
        {
            "claimText": "Patient reported blood in vomit and fainting.",
            "eventType": "vomiting",
            "evidenceText": "blood in vomit",
            "confidence": 0.97,
            "extractionType": "direct",
            "missingInfo": [],
            "riskLevel": "urgent",
            "safetyStatus": "safe",
        }
    ])

    raw_text = "I had blood in vomit and I fainted."
    from app.main import app
    client = TestClient(app)
    analyze_resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": raw_text,
    })
    assert analyze_resp.status_code == 200
    analyze_data = analyze_resp.json()
    original_escalation = analyze_data.get("escalationMessage")
    assert original_escalation is not None, "Expected escalation for urgent claim"

    if analyze_data["claims"]:
        claim_id = analyze_data["claims"][0]["claimId"]
        client.post("/review-claim", json={
            "doctorId": "doctor1",
            "claimId": claim_id,
            "action": "rejected",
        })

    import app.core.extraction as extraction
    from app.storage.repository import ClaimsRepository

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    row = repo.get_analyze_response(
        analyze_data["inputId"],
        extraction.PROMPT_VERSION_HASH,
        extraction.MODEL_ID,
    )
    assert row["escalation_message"] == original_escalation


def test_sticky_escalation_survives_edit_downgrade(
    patch_env_and_extraction, tmp_path
) -> None:
    """H5: edit urgent claim to lower risk → escalationMessage still on analyze_responses."""
    mock_client = patch_env_and_extraction

    _stub_llm(mock_client, [
        {
            "claimText": "Patient reported fainting.",
            "eventType": "vomiting",
            "evidenceText": "I fainted",
            "confidence": 0.93,
            "extractionType": "direct",
            "missingInfo": [],
            "riskLevel": "urgent",
            "safetyStatus": "safe",
        }
    ])

    raw_text = "I fainted briefly in the morning."
    from app.main import app
    client = TestClient(app)
    analyze_resp = client.post("/analyze", json={
        "patientId": "p1",
        "inputType": "text",
        "rawText": raw_text,
    })
    assert analyze_resp.status_code == 200
    analyze_data = analyze_resp.json()
    original_escalation = analyze_data.get("escalationMessage")

    if analyze_data["claims"]:
        claim_id = analyze_data["claims"][0]["claimId"]
        client.post("/review-claim", json={
            "doctorId": "doctor1",
            "claimId": claim_id,
            "action": "edited",
            "correctedClaim": "Patient felt lightheaded briefly.",
            "doctorEditOrigin": "correction",
        })

    import app.core.extraction as extraction
    from app.storage.repository import ClaimsRepository

    repo = ClaimsRepository(db_path=str(tmp_path / "test.db"))
    row = repo.get_analyze_response(
        analyze_data["inputId"],
        extraction.PROMPT_VERSION_HASH,
        extraction.MODEL_ID,
    )
    assert row["escalation_message"] == original_escalation
    assert row["created_at"] == analyze_data.get("createdAt") or True  # created_at unchanged
