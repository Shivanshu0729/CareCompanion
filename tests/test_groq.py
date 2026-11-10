from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from groq import APIConnectionError, APITimeoutError, AuthenticationError, NotFoundError, RateLimitError

from config.settings import Settings
from src.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMModelUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.llm.groq_client import GroqClient
from src.llm.provider import LLMMessage


def _settings() -> Settings:
    return Settings(
        groq_api_key="test-key",
        groq_model="test-model",
    )


def test_generate_returns_content_from_sdk() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        model="test-model",
        choices=[SimpleNamespace(message=SimpleNamespace(content="  Hello from Groq  "), finish_reason="stop")],
    )
    client = GroqClient(settings=_settings(), client=mock_client)
    response = client.generate([LLMMessage(role="user", content="Hi")])
    assert response.content == "Hello from Groq"
    assert response.model == "test-model"
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["messages"][0]["content"] == "Hi"


def test_missing_credentials() -> None:
    client = GroqClient(settings=Settings(groq_api_key="", groq_model="x"))
    with pytest.raises(LLMConfigurationError):
        client.generate([LLMMessage(role="user", content="Hi")])


def test_invalid_credentials() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        "invalid", response=MagicMock(status_code=401), body=None
    )
    client = GroqClient(settings=_settings(), client=mock_client)
    with pytest.raises(LLMAuthenticationError):
        client.generate([LLMMessage(role="user", content="Hi")])


def test_rate_limit() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RateLimitError(
        "slow down", response=MagicMock(status_code=429), body=None
    )
    client = GroqClient(settings=_settings(), client=mock_client)
    with pytest.raises(LLMRateLimitError):
        client.generate([LLMMessage(role="user", content="Hi")])


def test_timeout_and_connection() -> None:
    mock_client = MagicMock()
    client = GroqClient(settings=_settings(), client=mock_client)
    mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())
    with pytest.raises(LLMTimeoutError):
        client.generate([LLMMessage(role="user", content="Hi")])
    mock_client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
    with pytest.raises(LLMConnectionError):
        client.generate([LLMMessage(role="user", content="Hi")])


def test_unavailable_model() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = NotFoundError(
        "missing", response=MagicMock(status_code=404), body=None
    )
    client = GroqClient(settings=_settings(), client=mock_client)
    with pytest.raises(LLMModelUnavailableError):
        client.generate([LLMMessage(role="user", content="Hi")])
