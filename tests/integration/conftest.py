"""Shared fixtures for integration tests."""

import os
import tempfile
from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.storage.repository import ClaimsRepository


@pytest.fixture()
def db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture()
def repo(db_path: str) -> ClaimsRepository:
    return ClaimsRepository(db_path=db_path)


def make_mock_anthropic_client(input_tokens: int = 2000) -> MagicMock:
    mock_client = MagicMock()
    mock_token_result = MagicMock()
    mock_token_result.input_tokens = input_tokens
    mock_client.messages.count_tokens.return_value = mock_token_result
    return mock_client


def _ts() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


SAMPLE_URGENT_TRANSCRIPT = (
    "I had blood in my vomit this morning and I fainted briefly in the bathroom. "
    "I feel very weak and cannot keep any fluids down."
)

SAMPLE_SAFE_TRANSCRIPT = (
    "I had a mild headache this afternoon after lunch. No vomiting, no fever."
)

SAMPLE_MED_CHANGE_TRANSCRIPT = (
    "Should I stop taking my antibiotic? I think it is causing the vomiting."
)

SAMPLE_DIAGNOSIS_TRANSCRIPT = (
    "I think I have food poisoning from the curd rice I ate."
)

SAMPLE_ZERO_CLAIM_URGENT_TRANSCRIPT = (
    "I had chest pain this morning. I may be having a heart attack."
)
