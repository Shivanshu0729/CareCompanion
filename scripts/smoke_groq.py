from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import get_settings
from src.llm.groq_client import GroqClient
from src.llm.provider import LLMMessage


def main() -> int:
    settings = get_settings()
    if not settings.groq_configured():
        print("SKIP: GROQ_API_KEY and GROQ_MODEL are not configured.")
        return 0
    client = GroqClient(settings)
    response = client.generate(
        [
            LLMMessage(role="system", content="Reply with a single short sentence."),
            LLMMessage(role="user", content="Say that CareCompanion is ready."),
        ],
        temperature=0.1,
        max_tokens=40,
    )
    print(response.content)
    print(f"model={response.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
