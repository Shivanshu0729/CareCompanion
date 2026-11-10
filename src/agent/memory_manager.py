from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from src.database.models import Goal, MemoryRecord, Obstacle, Outcome, Recommendation, SessionSummary
from src.database.store import CareStore
from src.services.text_utils import relevance_score

logger = logging.getLogger(__name__)

TYPE_WEIGHTS = {
    "goal": 1.15,
    "obstacle": 1.1,
    "outcome": 1.12,
    "recommendation": 1.05,
    "preference": 0.95,
    "commitment": 1.0,
    "health": 0.8,
    "setting": 0.2,
}


@dataclass
class RetrievedMemory:
    kind: str
    content: str
    source: str
    score: float


class MemoryManager:
    def __init__(self, store: CareStore) -> None:
        self.store = store

    def retrieve(self, user_id: str, query: str, limit: int = 12) -> list[RetrievedMemory]:
        scored: list[RetrievedMemory] = []
        profile_query = bool(
            re.search(r"\b(tell me all about|what do you know about|about me|about \w+)\b", query.lower())
        )
        current_keys: set[str] = set()
        for memory in self.store.list_memories(user_id):
            if memory.memory_type == "setting" or not memory.confirmed or not memory.is_current:
                continue
            if memory.memory_key:
                if memory.memory_key in current_keys:
                    continue
                current_keys.add(memory.memory_key)
            score = relevance_score(query, memory.memory_content)
            if profile_query:
                score = max(score, 0.8)
            if memory.memory_type == "health":
                score = max(score, 0.25)
            score *= TYPE_WEIGHTS.get(memory.memory_type, 1.0)
            scored.append(
                RetrievedMemory(
                    kind=memory.memory_type,
                    content=memory.memory_content,
                    source=memory.source,
                    score=score,
                )
            )
        for goal in self.store.list_goals(user_id):
            score = relevance_score(query, goal.goal_description) * TYPE_WEIGHTS["goal"]
            scored.append(
                RetrievedMemory(
                    kind="goal",
                    content=f"{goal.goal_description} (status: {goal.status})",
                    source="user_reported",
                    score=score,
                )
            )
        for obstacle in self.store.list_obstacles(user_id):
            score = relevance_score(query, obstacle.obstacle_description) * TYPE_WEIGHTS["obstacle"]
            scored.append(
                RetrievedMemory(
                    kind="obstacle",
                    content=obstacle.obstacle_description,
                    source="user_reported",
                    score=score,
                )
            )
        for recommendation in self.store.list_recommendations(user_id):
            score = relevance_score(query, recommendation.recommendation) * TYPE_WEIGHTS["recommendation"]
            scored.append(
                RetrievedMemory(
                    kind="recommendation",
                    content=recommendation.recommendation,
                    source="ai_generated",
                    score=score,
                )
            )
        for outcome in self.store.list_outcomes(user_id):
            score = relevance_score(query, outcome.reported_outcome) * TYPE_WEIGHTS["outcome"]
            scored.append(
                RetrievedMemory(
                    kind="outcome",
                    content=outcome.reported_outcome,
                    source="user_reported",
                    score=score,
                )
            )
        for summary in ([] if profile_query else self.store.list_session_summaries(user_id)[:8]):
            summary_lower = summary.summary.lower()
            if any(
                key in current_keys
                and (
                    (key == "weight" and ("weight" in summary_lower or "weigh" in summary_lower))
                    or (key == "height" and "height" in summary_lower)
                    or (key == "age" and ("age" in summary_lower or "years old" in summary_lower))
                    or (key == "name" and ("name" in summary_lower or "call me" in summary_lower))
                )
                for key in current_keys
            ):
                continue
            score = relevance_score(query, summary.summary) * 0.7
            scored.append(
                RetrievedMemory(
                    kind="session_summary",
                    content=summary.summary,
                    source="ai_generated",
                    score=score,
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        unique: list[RetrievedMemory] = []
        seen: set[str] = set()
        for item in scored:
            key = f"{item.kind}:{item.content.lower()}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
            if len(unique) >= limit:
                break
        logger.debug(
            "memory retrieval user=%s query_type=%s returned=%d kinds=%s",
            user_id,
            "profile" if profile_query else "targeted",
            len(unique),
            sorted({item.kind for item in unique}),
        )
        return unique

    def demo_participant(self, user_id: str) -> str:
        for memory in self.store.list_memories(user_id, "setting"):
            if memory.memory_content.startswith("demo_participant:"):
                return memory.memory_content.split(":", 1)[1].strip() or "p01"
        return "p01"

    def set_demo_participant(self, user_id: str, participant_id: str) -> MemoryRecord:
        content = f"demo_participant:{participant_id}"
        existing = None
        for memory in self.store.list_memories(user_id, "setting"):
            if memory.memory_content.startswith("demo_participant:"):
                existing = memory
                break
        if existing:
            return self.store.update_memory(user_id, existing.id, content)
        return self.store.add_memory(
            MemoryRecord(
                user_id=user_id,
                memory_type="setting",
                memory_content=content,
                source="user_reported",
                confidence=1.0,
            )
        )
