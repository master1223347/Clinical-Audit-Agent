"""C2+H7 — Cache-token threshold tests (wt-01.md required test #2)."""

from unittest.mock import MagicMock

import pytest


def test_threshold_raises_below_sonnet_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock count_tokens to return below 1024 for sonnet; assert raises."""
    import app.core.extraction as extraction

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.input_tokens = 100  # well below 1024
    mock_client.messages.count_tokens.return_value = mock_result

    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-sonnet-4-6")

    with pytest.raises(RuntimeError, match="threshold"):
        extraction._check_cache_threshold()


def test_threshold_raises_below_opus_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.extraction as extraction

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.input_tokens = 500  # below 1024
    mock_client.messages.count_tokens.return_value = mock_result

    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-opus-4-7")

    with pytest.raises(RuntimeError, match="threshold"):
        extraction._check_cache_threshold()


def test_threshold_raises_below_haiku_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.extraction as extraction

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.input_tokens = 1500  # above sonnet/opus but below haiku 2048
    mock_client.messages.count_tokens.return_value = mock_result

    monkeypatch.setattr(extraction, "_client", mock_client)
    monkeypatch.setattr(extraction, "MODEL_ID", "claude-haiku-4-5")

    with pytest.raises(RuntimeError, match="threshold"):
        extraction._check_cache_threshold()


def test_threshold_passes_above_all_models(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.extraction as extraction

    for model_id in ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5"]:
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.input_tokens = 5000  # above all thresholds
        mock_client.messages.count_tokens.return_value = mock_result

        monkeypatch.setattr(extraction, "_client", mock_client)
        monkeypatch.setattr(extraction, "MODEL_ID", model_id)

        extraction._check_cache_threshold()  # should not raise


def test_token_counting_uses_anthropic_count_tokens_not_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """H7: token counting goes through client.messages.count_tokens, never len()."""
    import app.core.extraction as extraction

    call_count = 0

    class TrackingResult:
        input_tokens = 2000

    class TrackingMessages:
        def count_tokens(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return TrackingResult()

        def create(self, **kwargs):
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock()]
            mock_msg.content[0].text = "[]"
            mock_msg.usage.cache_read_input_tokens = 0
            mock_msg.usage.input_tokens = 100
            return mock_msg

    mock_client = MagicMock()
    mock_client.messages = TrackingMessages()
    monkeypatch.setattr(extraction, "_client", mock_client)

    extraction._check_cache_threshold()
    assert call_count >= 1, "count_tokens was not called during threshold check"
