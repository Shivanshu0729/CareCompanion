from __future__ import annotations

import logging
from typing import Any

from src.database.models import (
    Commitment,
    Conversation,
    Goal,
    MemoryRecord,
    Message,
    Obstacle,
    Outcome,
    Recommendation,
    SessionSummary,
    utcnow,
)
from src.services.text_utils import is_near_duplicate, memory_key as infer_memory_key, normalize_text

logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Raised when a Supabase data operation fails."""


class SupabaseCareStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def _execute(self, query: Any) -> list[dict[str, Any]]:
        try:
            result = query.execute()
        except Exception as exc:
            message = str(exc)
            if "PGRST204" in message and "conversation_id" in message:
                raise DatabaseError(
                    "The Supabase schema is missing conversation-linked columns. "
                    "Run migrations/002_conversation_memory_links.sql in the Supabase SQL editor, "
                    "then reload the app."
                ) from exc
            raise DatabaseError("The database request failed. Please try again.") from exc
        data = getattr(result, "data", None)
        if data is None:
            return []
        if isinstance(data, list):
            return data
        return [data]

    def _one(self, rows: list[dict[str, Any]], model_cls):
        if not rows:
            return None
        return model_cls.model_validate(rows[0])

    def create_conversation(self, user_id: str, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        rows = self._execute(
            self.client.table("conversations").insert(conversation.model_dump(mode="json"))
        )
        return self._one(rows, Conversation) or conversation

    def list_conversations(self, user_id: str) -> list[Conversation]:
        rows = self._execute(
            self.client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("is_pinned", desc=True)
            .order("updated_at", desc=True)
        )
        return [Conversation.model_validate(row) for row in rows]

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation | None:
        rows = self._execute(
            self.client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", conversation_id)
            .limit(1)
        )
        return self._one(rows, Conversation)

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> Conversation:
        rows = self._execute(
            self.client.table("conversations")
            .update({"title": title, "updated_at": utcnow().isoformat()})
            .eq("user_id", user_id)
            .eq("id", conversation_id)
        )
        conversation = self._one(rows, Conversation)
        if conversation is None:
            raise KeyError("Conversation not found.")
        return conversation

    def set_conversation_pinned(
        self, user_id: str, conversation_id: str, is_pinned: bool
    ) -> Conversation:
        rows = self._execute(
            self.client.table("conversations")
            .update({"is_pinned": is_pinned, "updated_at": utcnow().isoformat()})
            .eq("user_id", user_id)
            .eq("id", conversation_id)
        )
        conversation = self._one(rows, Conversation)
        if conversation is None:
            raise KeyError("Conversation not found.")
        return conversation

    def touch_conversation(self, user_id: str, conversation_id: str) -> None:
        self._execute(
            self.client.table("conversations")
            .update({"updated_at": utcnow().isoformat()})
            .eq("user_id", user_id)
            .eq("id", conversation_id)
        )

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        self._execute(
            self.client.table("messages")
            .delete()
            .eq("user_id", user_id)
            .eq("conversation_id", conversation_id)
        )
        self._execute(
            self.client.table("session_summaries")
            .delete()
            .eq("user_id", user_id)
            .eq("conversation_id", conversation_id)
        )
        self._execute(
            self.client.table("user_memories")
            .delete()
            .eq("user_id", user_id)
            .eq("conversation_id", conversation_id)
        )
        for table in ("goals", "recommendations", "commitments", "outcomes", "obstacles"):
            self._execute(
                self.client.table(table)
                .delete()
                .eq("user_id", user_id)
                .eq("conversation_id", conversation_id)
            )
        self._execute(
            self.client.table("conversations")
            .delete()
            .eq("user_id", user_id)
            .eq("id", conversation_id)
        )

    def add_message(self, user_id: str, conversation_id: str, role: str, content: str) -> Message:
        message = Message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,  # type: ignore[arg-type]
            content=content,
        )
        rows = self._execute(self.client.table("messages").insert(message.model_dump(mode="json")))
        self.touch_conversation(user_id, conversation_id)
        return self._one(rows, Message) or message

    def list_messages(
        self,
        user_id: str,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        query = (
            self.client.table("messages")
            .select("*")
            .eq("user_id", user_id)
            .eq("conversation_id", conversation_id)
            .order("created_at")
        )
        rows = self._execute(query)
        messages = [Message.model_validate(row) for row in rows]
        if limit is not None:
            return messages[-limit:]
        return messages

    def add_memory(self, memory: MemoryRecord) -> MemoryRecord:
        if memory.memory_key is None:
            memory.memory_key = infer_memory_key(memory.memory_content)
        existing = self.find_similar_memory(memory.user_id, memory.memory_type, memory.memory_content)
        if existing is not None:
            return existing
        if memory.memory_key and memory.is_current:
            previous = next(
                (
                    item
                    for item in self.list_memories(memory.user_id)
                    if item.id != memory.id
                    and item.memory_key == memory.memory_key
                    and item.confirmed
                    and item.is_current
                ),
                None,
            )
            if previous is not None:
                logger.debug(
                    "superseding memory user=%s memory_key=%s previous_id=%s",
                    memory.user_id,
                    memory.memory_key,
                    previous.id,
                )
                self._execute(
                    self.client.table("user_memories")
                    .update({
                        "is_current": False,
                        "superseded_by": memory.id,
                        "memory_key": memory.memory_key,
                        "updated_at": utcnow().isoformat(),
                    })
                    .eq("user_id", memory.user_id)
                    .eq("id", previous.id)
                )
        rows = self._execute(self.client.table("user_memories").insert(memory.model_dump(mode="json")))
        logger.debug(
            "memory stored user=%s memory_type=%s memory_key=%s confirmed=%s current=%s",
            memory.user_id,
            memory.memory_type,
            memory.memory_key,
            memory.confirmed,
            memory.is_current,
        )
        return self._one(rows, MemoryRecord) or memory

    def list_memories(self, user_id: str, memory_type: str | None = None) -> list[MemoryRecord]:
        query = self.client.table("user_memories").select("*").eq("user_id", user_id)
        if memory_type:
            query = query.eq("memory_type", memory_type)
        rows = self._execute(query.order("updated_at", desc=True))
        memories = [MemoryRecord.model_validate(row) for row in rows]
        for memory in memories:
            if memory.memory_key is None:
                memory.memory_key = infer_memory_key(memory.memory_content)
        return memories

    def update_memory(self, user_id: str, memory_id: str, memory_content: str) -> MemoryRecord:
        current = self._one(
            self._execute(
                self.client.table("user_memories")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", memory_id)
                .limit(1)
            ),
            MemoryRecord,
        )
        if current is None:
            raise KeyError("Memory not found.")
        replacement = MemoryRecord(
            user_id=user_id,
            conversation_id=current.conversation_id,
            memory_type=current.memory_type,
            memory_content=memory_content.strip(),
            source=current.source,
            confidence=current.confidence,
            confirmed=current.confirmed,
            memory_key=current.memory_key,
        )
        rows = self._execute(
            self.client.table("user_memories")
            .update({
                "is_current": False,
                "superseded_by": replacement.id,
                "updated_at": utcnow().isoformat(),
            })
            .eq("user_id", user_id)
            .eq("id", memory_id)
        )
        return self.add_memory(replacement)

    def delete_memory(self, user_id: str, memory_id: str) -> None:
        self._execute(
            self.client.table("user_memories").delete().eq("user_id", user_id).eq("id", memory_id)
        )

    def clear_memories(self, user_id: str) -> None:
        self._execute(self.client.table("user_memories").delete().eq("user_id", user_id))

    def add_session_summary(self, summary: SessionSummary) -> SessionSummary:
        rows = self._execute(
            self.client.table("session_summaries").insert(summary.model_dump(mode="json"))
        )
        return self._one(rows, SessionSummary) or summary

    def list_session_summaries(self, user_id: str) -> list[SessionSummary]:
        rows = self._execute(
            self.client.table("session_summaries")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        return [SessionSummary.model_validate(row) for row in rows]

    def add_goal(self, goal: Goal) -> Goal:
        existing = self.find_similar_goal(goal.user_id, goal.goal_description)
        if existing is not None:
            return existing
        rows = self._execute(self.client.table("goals").insert(goal.model_dump(mode="json")))
        return self._one(rows, Goal) or goal

    def list_goals(self, user_id: str) -> list[Goal]:
        rows = self._execute(
            self.client.table("goals").select("*").eq("user_id", user_id).order("updated_at", desc=True)
        )
        return [Goal.model_validate(row) for row in rows]

    def update_goal_status(self, user_id: str, goal_id: str, status: str) -> Goal:
        rows = self._execute(
            self.client.table("goals")
            .update({"status": status, "updated_at": utcnow().isoformat()})
            .eq("user_id", user_id)
            .eq("id", goal_id)
        )
        goal = self._one(rows, Goal)
        if goal is None:
            raise KeyError("Goal not found.")
        return goal

    def add_recommendation(self, recommendation: Recommendation) -> Recommendation:
        for existing in self.list_recommendations(recommendation.user_id):
            if is_near_duplicate(existing.recommendation, recommendation.recommendation):
                return existing
        rows = self._execute(
            self.client.table("recommendations").insert(recommendation.model_dump(mode="json"))
        )
        return self._one(rows, Recommendation) or recommendation

    def list_recommendations(self, user_id: str) -> list[Recommendation]:
        rows = self._execute(
            self.client.table("recommendations")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        return [Recommendation.model_validate(row) for row in rows]

    def add_commitment(self, commitment: Commitment) -> Commitment:
        for existing in self.list_commitments(commitment.user_id):
            if is_near_duplicate(existing.commitment_description, commitment.commitment_description):
                return existing
        rows = self._execute(
            self.client.table("commitments").insert(commitment.model_dump(mode="json"))
        )
        return self._one(rows, Commitment) or commitment

    def list_commitments(self, user_id: str) -> list[Commitment]:
        rows = self._execute(
            self.client.table("commitments")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        return [Commitment.model_validate(row) for row in rows]

    def add_outcome(self, outcome: Outcome) -> Outcome:
        rows = self._execute(self.client.table("outcomes").insert(outcome.model_dump(mode="json")))
        return self._one(rows, Outcome) or outcome

    def list_outcomes(self, user_id: str) -> list[Outcome]:
        rows = self._execute(
            self.client.table("outcomes")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        return [Outcome.model_validate(row) for row in rows]

    def add_obstacle(self, obstacle: Obstacle) -> Obstacle:
        for existing in self.list_obstacles(obstacle.user_id):
            if is_near_duplicate(existing.obstacle_description, obstacle.obstacle_description):
                return existing
        rows = self._execute(self.client.table("obstacles").insert(obstacle.model_dump(mode="json")))
        return self._one(rows, Obstacle) or obstacle

    def list_obstacles(self, user_id: str) -> list[Obstacle]:
        rows = self._execute(
            self.client.table("obstacles")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        return [Obstacle.model_validate(row) for row in rows]

    def find_similar_memory(self, user_id: str, memory_type: str, content: str) -> MemoryRecord | None:
        for memory in self.list_memories(user_id, memory_type):
            if is_near_duplicate(memory.memory_content, content):
                return memory
        return None

    def find_similar_goal(self, user_id: str, description: str) -> Goal | None:
        for goal in self.list_goals(user_id):
            if is_near_duplicate(goal.goal_description, description):
                return goal
        return None

    def latest_goal_for_hint(self, user_id: str, hint: str) -> Goal | None:
        goals = self.list_goals(user_id)
        if not goals:
            return None
        if not hint.strip():
            return goals[0]
        needle = normalize_text(hint)
        for goal in goals:
            haystack = normalize_text(goal.goal_description)
            if needle in haystack or haystack in needle:
                return goal
        return goals[0]

    def latest_recommendation(self, user_id: str) -> Recommendation | None:
        items = self.list_recommendations(user_id)
        return items[0] if items else None

    def latest_commitment(self, user_id: str) -> Commitment | None:
        items = self.list_commitments(user_id)
        return items[0] if items else None
