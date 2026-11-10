from __future__ import annotations

import re

from src.llm.exceptions import LLMResponseError
from src.llm.provider import LLMResponse

DIAGNOSIS_PATTERNS = [
    re.compile(r"\byou have (diabetes|cancer|hypertension|depression|anemia)\b", re.I),
    re.compile(r"\bthis (confirms|proves) you have\b", re.I),
    re.compile(r"\btake \d+\s?(mg|mcg|ml)\b", re.I),
    re.compile(r"\bstop taking your (medication|medicine|prescription)\b", re.I),
]


class ResponseValidator:
    def validate(self, response: LLMResponse, *, health_available: bool) -> str:
        content = (response.content or "").strip()
        if not content:
            raise LLMResponseError("The model returned an empty coaching response.")
        lowered = content.lower()
        if not health_available and any(
            phrase in lowered
            for phrase in ("your steps show", "your resting heart rate is", "your sleep score is")
        ):
            raise LLMResponseError(
                "The model claimed personal measurements that were not provided. The response was rejected."
            )
        for pattern in DIAGNOSIS_PATTERNS:
            if pattern.search(content):
                raise LLMResponseError(
                    "The model produced unsafe medical advice. The response was rejected."
                )
        return content
