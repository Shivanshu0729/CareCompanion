from __future__ import annotations

from copy import deepcopy

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


class InMemoryCareStore:
    """Test double that preserves user isolation. Not used for production memory."""

    def __init__(self) -> None:
        self.conversations: dict[str, Conversation] = {}
        self.messages: dict[str, Message] = {}
        self.memories: dict[str, MemoryRecord] = {}
        self.summaries: dict[str, SessionSummary] = {}
        self.goals: dict[str, Goal] = {}
        self.recommendations: dict[str, Recommendation] = {}
        self.commitments: dict[str, Commitment] = {}
        self.outcomes: dict[str, Outcome] = {}
        self.obstacles: dict[str, Obstacle] = {}

    def _owned(self, record, user_id: str):
        return record.user_id == user_id

    def create_conversation(self, user_id: str, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.conversations[conversation.id] = conversation
        return deepcopy(conversation)

    def list_conversations(self, user_id: str) -> list[Conversation]:
        items = [c for c in self.conversations.values() if c.user_id == user_id]
        items.sort(key=lambda item: (item.is_pinned, item.updated_at), reverse=True)
        return deepcopy(items)

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation | None:
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return None
        return deepcopy(conversation)

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> Conversation:
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise KeyError("Conversation not found.")
        conversation.title = title
        conversation.updated_at = utcnow()
        return deepcopy(conversation)

    def set_conversation_pinned(
        self, user_id: str, conversation_id: str, is_pinned: bool
    ) -> Conversation:
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise KeyError("Conversation not found.")
        conversation.is_pinned = is_pinned
        conversation.updated_at = utcnow()
        return deepcopy(conversation)

    def touch_conversation(self, user_id: str, conversation_id: str) -> None:
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise KeyError("Conversation not found.")
        conversation.updated_at = utcnow()

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return
        del self.conversations[conversation_id]
        for key, message in list(self.messages.items()):
            if message.conversation_id == conversation_id and message.user_id == user_id:
                del self.messages[key]
        for key, summary in list(self.summaries.items()):
            if summary.conversation_id == conversation_id and summary.user_id == user_id:
                del self.summaries[key]
        for key, memory in list(self.memories.items()):
            if memory.conversation_id == conversation_id and memory.user_id == user_id:
                del self.memories[key]
        for collection in (
            self.goals,
            self.recommendations,
            self.commitments,
            self.outcomes,
            self.obstacles,
        ):
            for key, record in list(collection.items()):
                if record.conversation_id == conversation_id and record.user_id == user_id:
                    del collection[key]

    def add_message(self, user_id: str, conversation_id: str, role: str, content: str) -> Message:
        if self.get_conversation(user_id, conversation_id) is None:
            raise KeyError("Conversation not found.")
        message = Message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,  # type: ignore[arg-type]
            content=content,
        )
        self.messages[message.id] = message
        self.touch_conversation(user_id, conversation_id)
        return deepcopy(message)

    def list_messages(
        self,
        user_id: str,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        items = [
            message
            for message in self.messages.values()
            if message.user_id == user_id and message.conversation_id == conversation_id
        ]
        items.sort(key=lambda item: item.created_at)
        if limit is not None:
            items = items[-limit:]
        return deepcopy(items)

    def add_memory(self, memory: MemoryRecord) -> MemoryRecord:
        if memory.memory_key is None:
            memory.memory_key = infer_memory_key(memory.memory_content)
        existing = self.find_similar_memory(memory.user_id, memory.memory_type, memory.memory_content)
        if existing is not None:
            return deepcopy(existing)
        if memory.memory_key and memory.is_current:
            for existing in self.memories.values():
                if (
                    existing.user_id == memory.user_id
                    and existing.memory_key == memory.memory_key
                    and existing.is_current
                ):
                    existing.is_current = False
                    existing.superseded_by = memory.id
                    existing.updated_at = utcnow()
        self.memories[memory.id] = memory
        return deepcopy(memory)

    def list_memories(self, user_id: str, memory_type: str | None = None) -> list[MemoryRecord]:
        items = [item for item in self.memories.values() if item.user_id == user_id]
        if memory_type:
            items = [item for item in items if item.memory_type == memory_type]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        for item in items:
            if item.memory_key is None:
                item.memory_key = infer_memory_key(item.memory_content)
        return deepcopy(items)

    def update_memory(self, user_id: str, memory_id: str, memory_content: str) -> MemoryRecord:
        memory = self.memories.get(memory_id)
        if memory is None or memory.user_id != user_id:
            raise KeyError("Memory not found.")
        memory.is_current = False
        replacement = MemoryRecord(
            user_id=user_id,
            conversation_id=memory.conversation_id,
            memory_type=memory.memory_type,
            memory_content=memory_content.strip(),
            source=memory.source,
            confidence=memory.confidence,
            confirmed=memory.confirmed,
            memory_key=memory.memory_key,
        )
        memory.superseded_by = replacement.id
        memory.updated_at = utcnow()
        self.memories[replacement.id] = replacement
        return deepcopy(replacement)

    def delete_memory(self, user_id: str, memory_id: str) -> None:
        memory = self.memories.get(memory_id)
        if memory is None or memory.user_id != user_id:
            return
        del self.memories[memory_id]

    def clear_memories(self, user_id: str) -> None:
        for key, memory in list(self.memories.items()):
            if memory.user_id == user_id:
                del self.memories[key]

    def add_session_summary(self, summary: SessionSummary) -> SessionSummary:
        self.summaries[summary.id] = summary
        return deepcopy(summary)

    def list_session_summaries(self, user_id: str) -> list[SessionSummary]:
        items = [item for item in self.summaries.values() if item.user_id == user_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return deepcopy(items)

    def add_goal(self, goal: Goal) -> Goal:
        existing = self.find_similar_goal(goal.user_id, goal.goal_description)
        if existing is not None:
            return deepcopy(existing)
        self.goals[goal.id] = goal
        return deepcopy(goal)

    def list_goals(self, user_id: str) -> list[Goal]:
        items = [item for item in self.goals.values() if item.user_id == user_id]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return deepcopy(items)

    def update_goal_status(self, user_id: str, goal_id: str, status: str) -> Goal:
        goal = self.goals.get(goal_id)
        if goal is None or goal.user_id != user_id:
            raise KeyError("Goal not found.")
        goal.status = status  # type: ignore[assignment]
        goal.updated_at = utcnow()
        return deepcopy(goal)

    def add_recommendation(self, recommendation: Recommendation) -> Recommendation:
        for existing in self.recommendations.values():
            if existing.user_id == recommendation.user_id and is_near_duplicate(
                existing.recommendation, recommendation.recommendation
            ):
                return deepcopy(existing)
        self.recommendations[recommendation.id] = recommendation
        return deepcopy(recommendation)

    def list_recommendations(self, user_id: str) -> list[Recommendation]:
        items = [item for item in self.recommendations.values() if item.user_id == user_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return deepcopy(items)

    def add_commitment(self, commitment: Commitment) -> Commitment:
        for existing in self.commitments.values():
            if existing.user_id == commitment.user_id and is_near_duplicate(
                existing.commitment_description, commitment.commitment_description
            ):
                return deepcopy(existing)
        self.commitments[commitment.id] = commitment
        return deepcopy(commitment)

    def list_commitments(self, user_id: str) -> list[Commitment]:
        items = [item for item in self.commitments.values() if item.user_id == user_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return deepcopy(items)

    def add_outcome(self, outcome: Outcome) -> Outcome:
        self.outcomes[outcome.id] = outcome
        return deepcopy(outcome)

    def list_outcomes(self, user_id: str) -> list[Outcome]:
        items = [item for item in self.outcomes.values() if item.user_id == user_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return deepcopy(items)

    def add_obstacle(self, obstacle: Obstacle) -> Obstacle:
        for existing in self.obstacles.values():
            if existing.user_id == obstacle.user_id and is_near_duplicate(
                existing.obstacle_description, obstacle.obstacle_description
            ):
                return deepcopy(existing)
        self.obstacles[obstacle.id] = obstacle
        return deepcopy(obstacle)

    def list_obstacles(self, user_id: str) -> list[Obstacle]:
        items = [item for item in self.obstacles.values() if item.user_id == user_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return deepcopy(items)

    def find_similar_memory(self, user_id: str, memory_type: str, content: str) -> MemoryRecord | None:
        for memory in self.memories.values():
            if (
                memory.user_id == user_id
                and memory.memory_type == memory_type
                and is_near_duplicate(memory.memory_content, content)
            ):
                return deepcopy(memory)
        return None

    def find_similar_goal(self, user_id: str, description: str) -> Goal | None:
        for goal in self.goals.values():
            if goal.user_id == user_id and is_near_duplicate(goal.goal_description, description):
                return deepcopy(goal)
        return None

    def latest_goal_for_hint(self, user_id: str, hint: str) -> Goal | None:
        goals = self.list_goals(user_id)
        if not hint.strip():
            return goals[0] if goals else None
        needle = normalize_text(hint)
        for goal in goals:
            if needle in normalize_text(goal.goal_description) or normalize_text(goal.goal_description) in needle:
                return goal
        return goals[0] if goals else None

    def latest_recommendation(self, user_id: str) -> Recommendation | None:
        items = self.list_recommendations(user_id)
        return items[0] if items else None

    def latest_commitment(self, user_id: str) -> Commitment | None:
        items = self.list_commitments(user_id)
        return items[0] if items else None
