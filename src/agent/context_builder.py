from __future__ import annotations

import logging

from src.agent.memory_manager import RetrievedMemory
from src.data.health_service import HealthContext
from src.database.models import Message
from src.llm.prompts import COACH_SYSTEM_PROMPT
from src.llm.provider import LLMMessage
from src.services.text_utils import is_single_value_key

logger = logging.getLogger(__name__)


class ContextBuilder:
    def build(
        self,
        *,
        user_message: str,
        history: list[Message],
        memories: list[RetrievedMemory],
        health: HealthContext,
        max_history: int = 12,
    ) -> list[LLMMessage]:
        categorized_blocks: dict[str, list[str]] = {
            "User Profile & Preferences": [],
            "Active Goals & Ongoing Projects": [],
            "Project Context & Progress": [],
            "User-Reported Health Limits & Facts": [],
            "Other Stored Memory": [],
            "Historical Information (Past Values - Not Current)": [],
        }

        seen_single_value_keys: set[str] = set()

        if memories:
            for memory in memories:
                kind = memory.kind.lower()
                content = memory.content
                source = memory.source
                is_historical = getattr(memory, "is_historical", False)

                if is_historical:
                    categorized_blocks["Historical Information (Past Values - Not Current)"].append(
                        f"- [Historical/Past] {content} (Superseded older value)"
                    )
                    continue

                if memory.key and is_single_value_key(memory.key):
                    if memory.key in seen_single_value_keys:
                        continue
                    seen_single_value_keys.add(memory.key)

                if kind in {"profile", "preference"}:
                    categorized_blocks["User Profile & Preferences"].append(f"- {content}")
                elif kind in {"goal"}:
                    categorized_blocks["Active Goals & Ongoing Projects"].append(f"- {content}")
                elif kind in {"context", "progress"}:
                    categorized_blocks["Project Context & Progress"].append(f"- {content}")
                elif kind == "health":
                    categorized_blocks["User-Reported Health Limits & Facts"].append(f"- {content} (user-reported)")
                else:
                    categorized_blocks["Other Stored Memory"].append(f"- [{kind}] {content}")

        memory_sections = []
        for header, items in categorized_blocks.items():
            if items:
                memory_sections.append(f"### {header}\n" + "\n".join(items))

        if not memory_sections:
            memory_context_str = "- None stored yet."
        else:
            memory_context_str = "\n\n".join(memory_sections)
            memory_context_str += (
                "\n\n[MEMORY CONSISTENCY RULES]\n"
                "1. Values in 'User-Reported Health Limits & Facts', 'User Profile & Preferences', and 'Active Goals' are CURRENT active values. "
                "Always use these when answering questions about current user attributes (e.g. current weight, height, age, name).\n"
                "2. When the user asks 'What is my current weight?' or asks about their weight, answer directly with the latest confirmed current weight from 'User-Reported Health Limits & Facts'. "
                "Never use an outdated number or a past value.\n"
                "3. Values in 'Historical Information' are past, superseded facts. NEVER state them as current values; "
                "only reference them when the user explicitly asks about their previous or past history."
            )

        health_lines = [
            f"Source: {health.source_label}",
            f"Demo participant ID: {health.participant_id}",
            f"Measurement range: {health.date_start or 'unknown'} to {health.date_end or 'unknown'}",
            f"Available metrics: {', '.join(health.available_metrics) or 'none'}",
        ]
        health_lines.extend(f"Note: {note}" for note in health.notes)
        if health.recent_rows:
            health_lines.append("Recent measured rows:")
            for row in health.recent_rows:
                health_lines.append(f"- {row}")
        else:
            health_lines.append("No measured rows were retrieved for this request.")

        system = (
            COACH_SYSTEM_PROMPT
            + "\n\n## Persistent Long-Term Memory Retrieved for this User:\n"
            + memory_context_str
            + "\n\n## Research Health Measurements (PMData):\n"
            + "\n".join(health_lines)
        )

        messages = [LLMMessage(role="system", content=system)]
        recent = history[-max_history:]
        for item in recent:
            if item.role in {"user", "assistant"}:
                messages.append(LLMMessage(role=item.role, content=item.content))
        messages.append(LLMMessage(role="user", content=user_message))

        logger.debug(
            "coach context built history_messages=%d memory_items=%d health_rows=%d",
            len(recent),
            len(memories),
            len(health.recent_rows),
        )
        return messages
