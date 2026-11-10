from src.database.store import CareStore
from src.llm.prompts import build_title_from_message


class ConversationService:
    def __init__(self, store: CareStore) -> None:
        self.store = store

    def create(self, user_id: str, title: str | None = None):
        return self.store.create_conversation(user_id, title or "New conversation")

    def list(self, user_id: str):
        return self.store.list_conversations(user_id)

    def rename(self, user_id: str, conversation_id: str, title: str):
        cleaned = title.strip() or "New conversation"
        return self.store.rename_conversation(user_id, conversation_id, cleaned)

    def set_pinned(self, user_id: str, conversation_id: str, is_pinned: bool):
        return self.store.set_conversation_pinned(user_id, conversation_id, is_pinned)

    def delete(self, user_id: str, conversation_id: str) -> None:
        self.store.delete_conversation(user_id, conversation_id)

    def title_from_first_message(self, message: str) -> str:
        return build_title_from_message(message)
