from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import re

from src.database.models import Goal, MemoryRecord, Obstacle, Outcome, Recommendation, SessionSummary
from src.database.store import CareStore
from src.services.text_utils import (
    SINGLE_VALUE_KEYS,
    detect_query_intents,
    is_historical_query,
    is_single_value_key,
    relevance_score,
)

logger = logging.getLogger(__name__)

TYPE_WEIGHTS = {
    "health": 1.25,        # High priority for safety & health context
    "goal": 1.20,          # High priority for career, learning, and fitness targets
    "context": 1.20,       # Projects, requirements, and technical decisions
    "progress": 1.15,      # Milestones, task completion, and status
    "profile": 1.15,       # Education, profession, skills, identity
    "preference": 1.05,    # Style, diet, technical preferences
    "obstacle": 1.10,
    "outcome": 1.10,
    "recommendation": 1.00,
    "commitment": 1.00,
    "setting": 0.20,
}


@dataclass
class RetrievedMemory:
    kind: str
    content: str
    source: str
    score: float
    importance: float = 0.7
    key: str | None = None
    is_historical: bool = False


class MemoryManager:
    def __init__(self, store: CareStore) -> None:
        self.store = store

    @staticmethod
    def is_profile_query(query: str) -> bool:
        lowered = query.lower()
        return bool(
            re.search(
                r"\b(tell me (?:all )?about|what do you know about|about me|who am i|"
                r"my profile|my background|what health issue|what condition|what are my conditions|"
                r"what are my goals|my current goals|my projects|what projects)\b",
                lowered,
            )
        )

    def retrieve(self, user_id: str, query: str, limit: int = 12) -> list[RetrievedMemory]:
        scored: list[RetrievedMemory] = []
        profile_query = self.is_profile_query(query)
        historical_query = is_historical_query(query)
        intents = detect_query_intents(query)
        current_keys: set[str] = set()
        active_key_values: dict[str, str] = {}
        now = datetime.now(timezone.utc)

        # 1. Retrieve and score general persistent memories
        for memory in self.store.list_memories(user_id):
            if memory.memory_type == "setting" or not memory.confirmed:
                continue

            # Historical memory retrieval when user asks about previous/past values
            if not memory.is_current:
                if not historical_query:
                    continue
                rel = relevance_score(query, memory.memory_content)
                content_intents = detect_query_intents(memory.memory_content)
                if rel <= 0.05 and not (intents & content_intents):
                    continue
                scored.append(
                    RetrievedMemory(
                        kind=memory.memory_type,
                        content=memory.memory_content,
                        source="user_reported_historical",
                        score=0.90 + rel,
                        importance=0.6,
                        key=memory.memory_key,
                        is_historical=True,
                    )
                )
                continue

            if memory.memory_key:
                if memory.memory_key in current_keys:
                    continue
                current_keys.add(memory.memory_key)
                active_key_values[memory.memory_key] = memory.memory_content.lower()

            rel = relevance_score(query, memory.memory_content)
            content_intents = detect_query_intents(memory.memory_content)
            has_topic_match = bool(intents & content_intents)

            # Irrelevant exclusion: Do not retrieve unrelated memories without token or topic affinity
            if not profile_query and rel <= 0.05 and not has_topic_match:
                continue

            # Recency bonus (within 30 days)
            age_days = (now - memory.updated_at).total_seconds() / 86400.0 if memory.updated_at else 0.0
            recency_bonus = 0.10 * max(0.0, 1.0 - (age_days / 30.0))

            # Intent-based affinity bonus
            intent_bonus = 0.0
            if "learning" in intents and (memory.memory_type in {"goal", "context"} or "learn" in memory.memory_content.lower()):
                intent_bonus += 0.35
            if "career" in intents and (memory.memory_type in {"goal", "profile"} or "internship" in memory.memory_content.lower() or "job" in memory.memory_content.lower()):
                intent_bonus += 0.35
            if "project" in intents and (memory.memory_type in {"context", "progress"} or "project" in memory.memory_content.lower()):
                intent_bonus += 0.40
            if "health" in intents and memory.memory_type == "health":
                intent_bonus += 0.45

            if profile_query:
                rel = max(rel, 0.80)
            elif memory.memory_type == "health":
                rel = max(rel, 0.30)

            # Hybrid scoring formula
            importance = getattr(memory, "importance", 0.7)
            confidence = getattr(memory, "confidence", 0.7)
            base_score = (0.40 * rel) + (0.25 * importance) + (0.15 * confidence) + recency_bonus + intent_bonus
            final_score = base_score * TYPE_WEIGHTS.get(memory.memory_type, 1.0)

            scored.append(
                RetrievedMemory(
                    kind=memory.memory_type,
                    content=memory.memory_content,
                    source=memory.source,
                    score=final_score,
                    importance=importance,
                    key=memory.memory_key,
                    is_historical=False,
                )
            )

        # 2. Score Goals from goals table
        for goal in self.store.list_goals(user_id):
            if goal.status == "completed" and not profile_query and "project" not in intents:
                continue
            rel = relevance_score(query, goal.goal_description)
            intent_bonus = 0.30 if ("learning" in intents or "career" in intents) else 0.0
            score = ((0.50 * rel) + (0.35 * 0.8) + intent_bonus) * TYPE_WEIGHTS["goal"]
            scored.append(
                RetrievedMemory(
                    kind="goal",
                    content=f"{goal.goal_description} (status: {goal.status})",
                    source="user_reported",
                    score=score,
                    importance=0.85,
                )
            )

        # 3. Score Obstacles
        for obstacle in self.store.list_obstacles(user_id):
            rel = relevance_score(query, obstacle.obstacle_description)
            content_intents = detect_query_intents(obstacle.obstacle_description)
            has_topic_match = bool(intents & content_intents)
            if not profile_query and rel <= 0.05 and not has_topic_match:
                continue
            scored.append(
                RetrievedMemory(
                    kind="obstacle",
                    content=obstacle.obstacle_description,
                    source="user_reported",
                    score=rel * TYPE_WEIGHTS["obstacle"],
                    importance=0.75,
                )
            )

        # 4. Score Recommendations
        for recommendation in self.store.list_recommendations(user_id):
            rel = relevance_score(query, recommendation.recommendation)
            content_intents = detect_query_intents(recommendation.recommendation)
            has_topic_match = bool(intents & content_intents)
            if not profile_query and rel <= 0.05 and not has_topic_match:
                continue
            scored.append(
                RetrievedMemory(
                    kind="recommendation",
                    content=recommendation.recommendation,
                    source="ai_generated",
                    score=rel * TYPE_WEIGHTS["recommendation"],
                    importance=0.65,
                )
            )

        # 5. Score Outcomes
        for outcome in self.store.list_outcomes(user_id):
            rel = relevance_score(query, outcome.reported_outcome)
            content_intents = detect_query_intents(outcome.reported_outcome)
            has_topic_match = bool(intents & content_intents)
            if not profile_query and rel <= 0.05 and not has_topic_match:
                continue
            scored.append(
                RetrievedMemory(
                    kind="outcome",
                    content=outcome.reported_outcome,
                    source="user_reported",
                    score=rel * TYPE_WEIGHTS["outcome"],
                    importance=0.75,
                )
            )

        # 6. Score Session Summaries with Conflict Suppression
        is_weight_query = bool(re.search(r"\b(weigh|weight|kg|lbs)\b", query.lower()))
        is_height_query = bool(re.search(r"\b(height|tall|cm|feet|inches)\b", query.lower()))
        is_age_query = bool(re.search(r"\b(age|years old)\b", query.lower()))

        for summary in ([] if profile_query else self.store.list_session_summaries(user_id)[:8]):
            summary_lower = summary.summary.lower()

            # Suppress outdated session summaries if an active current memory contradicts it or query targets single-value facts
            suppress = False
            if (is_weight_query or "weight" in current_keys) and any(w in summary_lower for w in ("weight", "weigh", "kg", "lbs")):
                suppress = True
            elif (is_height_query or "height" in current_keys) and any(h in summary_lower for h in ("height", "cm", "feet", "inches", "tall")):
                suppress = True
            elif (is_age_query or "age" in current_keys) and any(a in summary_lower for a in ("age", "years old")):
                suppress = True
            else:
                for key in current_keys:
                    if key == "name" and ("name" in summary_lower or "call me" in summary_lower):
                        suppress = True
                        break
                    if key.startswith("learning_goal_") and ("learning" in summary_lower or "learn" in summary_lower):
                        suppress = True
                        break
                    if key == "diet_type" and ("vegetarian" in summary_lower or "vegan" in summary_lower or "diet" in summary_lower):
                        suppress = True
                        break

            if suppress:
                continue

            rel = relevance_score(query, summary.summary) * 0.65
            scored.append(
                RetrievedMemory(
                    kind="session_summary",
                    content=summary.summary,
                    source="ai_generated",
                    score=rel,
                    importance=0.5,
                )
            )

        # Sort by final score descending
        scored.sort(key=lambda item: item.score, reverse=True)

        # Deduplicate results
        unique: list[RetrievedMemory] = []
        seen: set[str] = set()
        for item in scored:
            key = f"{item.kind}:{item.content.lower().strip()}"
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

    @staticmethod
    def profile_response(memories: list[RetrievedMemory]) -> str:
        lines = ["Here is what I currently remember across your profile and conversations:"]
        categorized: dict[str, list[str]] = {}
        for memory in memories:
            if getattr(memory, "is_historical", False):
                continue
            label = memory.kind.replace("_", " ").title()
            qualifier = " (user-reported)" if memory.source == "user_reported" else ""
            categorized.setdefault(label, []).append(f"{memory.content}{qualifier}")

        for cat, items in categorized.items():
            lines.append(f"\n**{cat}**:")
            for it in items:
                lines.append(f"- {it}")

        return "\n".join(lines)

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
