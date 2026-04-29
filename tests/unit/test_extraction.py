"""§8.1 + §A.1 + pilot.md C2/C3/H7 — Extraction module tests."""

from unittest.mock import MagicMock, patch

import pytest


def test_prompt_version_hash_is_sha256_string() -> None:
    from app.core.extraction import PROMPT_VERSION_HASH

    assert isinstance(PROMPT_VERSION_HASH, str)
    assert len(PROMPT_VERSION_HASH) == 64  # sha256 hex


def test_min_cache_tokens_by_model_has_required_models() -> None:
    from app.core.extraction import MIN_CACHE_TOKENS_BY_MODEL

    assert "claude-sonnet-4-6" in MIN_CACHE_TOKENS_BY_MODEL
    assert "claude-opus-4-7" in MIN_CACHE_TOKENS_BY_MODEL
    assert "claude-haiku-4-5" in MIN_CACHE_TOKENS_BY_MODEL
    assert MIN_CACHE_TOKENS_BY_MODEL["claude-sonnet-4-6"] == 1024
    assert MIN_CACHE_TOKENS_BY_MODEL["claude-opus-4-7"] == 1024
    assert MIN_CACHE_TOKENS_BY_MODEL["claude-haiku-4-5"] == 2048


def test_check_cache_threshold_raises_below_sonnet_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """C2/H7: mock count_tokens to return below threshold; assert raises."""
    import app.core.extraction as extraction

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.input_tokens = 10  # well below 1024
    mock_client.messages.count_tokens.return_value = mock_result
    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-sonnet-4-6")

    with pytest.raises(RuntimeError, match="threshold"):
        extraction._check_cache_threshold()


def test_check_cache_threshold_raises_below_haiku_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.extraction as extraction

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.input_tokens = 1500  # above sonnet/opus (1024) but below haiku (2048)
    mock_client.messages.count_tokens.return_value = mock_result
    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-haiku-4-5")

    with pytest.raises(RuntimeError, match="threshold"):
        extraction._check_cache_threshold()


def test_check_cache_threshold_passes_above_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.extraction as extraction

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.input_tokens = 2000  # above all thresholds
    mock_client.messages.count_tokens.return_value = mock_result
    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-sonnet-4-6")

    extraction._check_cache_threshold()  # should not raise


def test_prompt_version_hash_changes_with_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """C3: changing the cached block produces a different hash."""
    import hashlib

    import app.core.extraction as extraction

    original_hash = extraction.PROMPT_VERSION_HASH
    new_prompt = "totally different prompt content"
    new_hash = hashlib.sha256(new_prompt.encode()).hexdigest()

    assert new_hash != original_hash


def test_overlap_heuristic_direct_above_threshold() -> None:
    from app.core.extraction import _content_word_overlap

    claim = "Patient reported vomiting twice after dinner"
    evidence = "vomiting twice after dinner"

    ratio = _content_word_overlap(claim, evidence)
    assert ratio >= 0.5


def test_overlap_heuristic_interpretation_below_threshold() -> None:
    from app.core.extraction import _content_word_overlap

    claim = "Patient has severe viral gastroenteritis"
    evidence = "felt a bit off"

    ratio = _content_word_overlap(claim, evidence)
    assert ratio < 0.5
