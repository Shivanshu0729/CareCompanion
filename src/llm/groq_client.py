from __future__ import annotations

from typing import Sequence

from groq import Groq
from groq import APIConnectionError, APIStatusError, APITimeoutError
from groq import AuthenticationError, NotFoundError, RateLimitError

from config.settings import Settings, get_settings
from src.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMModelUnavailableError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from src.llm.provider import LLMMessage, LLMResponse


class GroqClient:
    def __init__(
        self,
        settings: Settings | None = None,
        client: Groq | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def _require_config(self) -> None:
        if not self.settings.groq_api_key.strip():
            raise LLMConfigurationError(
                "The AI service key is not configured. Add it to your environment or Streamlit secrets."
            )

    def _get_client(self) -> Groq:
        if self._client is not None:
            return self._client
        self._require_config()
        self._client = Groq(
            api_key=self.settings.groq_api_key,
            timeout=self.settings.groq_timeout_seconds,
            max_retries=self.settings.groq_max_retries,
        )
        return self._client

    def generate(
        self,
        messages: Sequence[LLMMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 900,
    ) -> LLMResponse:
        if not messages:
            raise LLMResponseError("Cannot generate a response without messages.")
        client = self._get_client()
        model = self.settings.groq_model.strip()
        if not model:
            raise LLMConfigurationError("The AI model is not configured. Set a current model ID in your environment.")
        payload = [message.to_api() for message in messages]
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=payload,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AuthenticationError as exc:
            raise LLMAuthenticationError(
                "The AI service rejected the access key. Check your configuration and try again."
            ) from exc
        except RateLimitError as exc:
            raise LLMRateLimitError(
                "The AI service is busy. Wait a moment and send the message again."
            ) from exc
        except APITimeoutError as exc:
            raise LLMTimeoutError(
                "The AI request timed out. Please try again."
            ) from exc
        except APIConnectionError as exc:
            raise LLMConnectionError(
                "Could not reach the AI service. Check your network connection and try again."
            ) from exc
        except NotFoundError as exc:
            raise LLMModelUnavailableError(
                "The configured AI model is unavailable. Update the model configuration."
            ) from exc
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status in {401, 403}:
                raise LLMAuthenticationError(
                    "The AI service rejected the request. Check the service configuration."
                ) from exc
            if status == 404:
                raise LLMModelUnavailableError(
                    "The configured AI model is unavailable. Update the model configuration."
                ) from exc
            if status == 429:
                raise LLMRateLimitError(
                    "The AI service is busy. Wait a moment and try again."
                ) from exc
            raise LLMResponseError(
                "The AI service returned an error and no substitute response was generated."
            ) from exc
        except Exception as exc:
            raise LLMResponseError(
                "The AI service could not generate a response. No fallback answer was created."
            ) from exc

        choices = getattr(completion, "choices", None) or []
        if not choices:
            raise LLMResponseError("The AI service returned no response choices.")
        message = choices[0].message
        content = (getattr(message, "content", None) or "").strip()
        if not content:
            raise LLMResponseError("The AI service returned an empty message.")
        finish_reason = getattr(choices[0], "finish_reason", None)
        used_model = getattr(completion, "model", None) or model
        return LLMResponse(content=content, model=used_model, finish_reason=finish_reason)
