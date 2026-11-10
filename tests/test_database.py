from __future__ import annotations

from src.database.models import Goal, MemoryRecord
from src.database.in_memory import InMemoryCareStore


def test_insert_and_retrieve_conversation(store: InMemoryCareStore, user_a: str) -> None:
    conversation = store.create_conversation(user_a, "Sleep plan")
    fetched = store.get_conversation(user_a, conversation.id)
    assert fetched is not None
    assert fetched.title == "Sleep plan"
    listed = store.list_conversations(user_a)
    assert listed[0].id == conversation.id


def test_message_round_trip(store: InMemoryCareStore, user_a: str) -> None:
    conversation = store.create_conversation(user_a, "Chat")
    store.add_message(user_a, conversation.id, "user", "hello")
    store.add_message(user_a, conversation.id, "assistant", "hi")
    messages = store.list_messages(user_a, conversation.id)
    assert [item.role for item in messages] == ["user", "assistant"]
    assert messages[0].content == "hello"


def test_memory_and_goal_insert(store: InMemoryCareStore, user_a: str) -> None:
    goal = store.add_goal(Goal(user_id=user_a, goal_description="Walk more"))
    memory = store.add_memory(
        MemoryRecord(user_id=user_a, memory_type="goal", memory_content="Walk more", source="user_reported")
    )
    assert store.list_goals(user_a)[0].id == goal.id
    assert store.list_memories(user_a)[0].id == memory.id
