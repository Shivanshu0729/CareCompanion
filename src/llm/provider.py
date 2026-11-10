from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str | list[dict[str, Any]]

    def to_api(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    finish_reason: str | None = None


class LLMProvider(Protocol):
    def generate(
        self,
        messages: Sequence[LLMMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 900,
    ) -> LLMResponse:
        """Generate a chat completion from the hosted provider."""
