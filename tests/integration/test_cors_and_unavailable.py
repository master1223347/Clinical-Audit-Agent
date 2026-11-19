"""CORS for the localhost doctor portal and 503 when LLM credentials are missing."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAIMS_DB_PATH", str(tmp_path / "test.db"))


def test_review_claim_preflight_allows_portal_origin() -> None:
    from app.main import app

    resp = TestClient(app).options(
        "/review-claim",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_preflight_rejects_unknown_origin() -> None:
    from app.main import app

    resp = TestClient(app).options(
        "/review-claim",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in resp.headers


def test_precompute_returns_503_without_credentials(monkeypatch) -> None:
    import anthropic

    import app.core.extraction as extraction

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(extraction, "_client", anthropic.Anthropic())

    from app.main import app

    resp = TestClient(app).post(
        "/precompute", json=[{"transcript_id": "t-1", "raw_text": "I threw up."}]
    )
    assert resp.status_code == 503
    assert "ANTHROPIC_API_KEY" in resp.json()["detail"]
