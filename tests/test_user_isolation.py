from __future__ import annotations

from src.database.models import Goal, MemoryRecord
from src.database.in_memory import InMemoryCareStore


def test_users_cannot_read_each_other_records(
    store: InMemoryCareStore, user_a: str, user_b: str
) -> None:
    conversation = store.create_conversation(user_a, "Private A")
    store.add_message(user_a, conversation.id, "user", "secret sleep goal")
    store.add_goal(Goal(user_id=user_a, goal_description="Private goal"))
    store.add_memory(
        MemoryRecord(user_id=user_a, memory_type="preference", memory_content="Private preference")
    )
    assert store.list_conversations(user_b) == []
    assert store.get_conversation(user_b, conversation.id) is None
    assert store.list_messages(user_b, conversation.id) == []
    assert store.list_goals(user_b) == []
    assert store.list_memories(user_b) == []
    store.delete_conversation(user_b, conversation.id)
    assert store.get_conversation(user_a, conversation.id) is not None
