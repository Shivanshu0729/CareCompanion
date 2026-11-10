from __future__ import annotations

from src.database.in_memory import InMemoryCareStore
from src.services.conversation_service import ConversationService


def test_create_continue_and_delete(store: InMemoryCareStore, user_a: str) -> None:
    service = ConversationService(store)
    first = service.create(user_a, "One")
    second = service.create(user_a, "Two")
    store.add_message(user_a, first.id, "user", "hello from one")
    continued = store.list_messages(user_a, first.id)
    assert continued[0].content == "hello from one"
    assert {item.title for item in service.list(user_a)} == {"One", "Two"}
    service.rename(user_a, second.id, "Two renamed")
    assert store.get_conversation(user_a, second.id).title == "Two renamed"
    service.delete(user_a, first.id)
    assert store.get_conversation(user_a, first.id) is None
    assert store.list_messages(user_a, first.id) == []
    assert store.get_conversation(user_a, second.id) is not None
