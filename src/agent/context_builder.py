from __future__ import annotations

import logging

from src.agent.memory_manager import RetrievedMemory
from src.data.health_service import HealthContext
from src.database.models import Message
from src.llm.prompts import COACH_SYSTEM_PROMPT
from src.llm.provider import LLMMessage

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
        memory_lines = []
        if memories:
            for memory in memories:
                memory_lines.append(f"- [{memory.kind} | {memory.source}] {memory.content}")
        else:
            memory_lines.append("- None stored yet.")

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
            + "\n\nLong-term memory retrieved for this request:\n"
            + "\n".join(memory_lines)
            + "\n\nHealth measurements retrieved for this request:\n"
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
