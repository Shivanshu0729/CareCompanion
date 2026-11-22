from __future__ import annotations

from src.database.store import CareStore
from src.llm.provider import LLMProvider
from src.services.title_generator import TitleGenerator


class ConversationService:
    def __init__(self, store: CareStore, llm: LLMProvider | None = None) -> None:
        self.store = store
        self.llm = llm
        self.title_generator = TitleGenerator(llm)

    def create(self, user_id: str, title: str | None = None):
        return self.store.create_conversation(user_id, title or "New conversation")

    def list(self, user_id: str):
        return self.store.list_conversations(user_id)

    def get(self, user_id: str, conversation_id: str):
        return self.store.get_conversation(user_id, conversation_id)

    def rename(self, user_id: str, conversation_id: str, title: str):
        cleaned = title.strip() or "New conversation"
        return self.store.rename_conversation(user_id, conversation_id, cleaned)

    def set_pinned(self, user_id: str, conversation_id: str, is_pinned: bool):
        return self.store.set_conversation_pinned(user_id, conversation_id, is_pinned)

    def delete(self, user_id: str, conversation_id: str) -> None:
        conversation = self.store.get_conversation(user_id, conversation_id)
        if conversation is None:
            raise KeyError("Conversation not found.")
        self.store.delete_conversation(user_id, conversation_id)

    def title_from_first_message(self, message: str) -> str:
        return self.title_generator.generate_title(message)

    def auto_rename_if_needed(
        self,
        user_id: str,
        conversation_id: str,
        first_message: str,
        existing_history_count: int = 0,
    ) -> str | None:
        """Automatically rename a conversation on its first message if it has a default title."""
        conversation = self.store.get_conversation(user_id, conversation_id)
        if conversation is None:
            return None

        # Check if the title is still a default/placeholder
        is_default_title = (conversation.title or "").strip().lower() in {
            "new conversation",
            "new chat",
            "untitled",
            "",
        }

        # If user manually changed title or already has prior messages, do not overwrite
        if not is_default_title or existing_history_count > 0:
            return conversation.title

        new_title = self.title_from_first_message(first_message)
        if (
            new_title
            and new_title.strip().lower() not in {"new conversation", "untitled", ""}
            and new_title != conversation.title
        ):
            updated = self.rename(user_id, conversation_id, new_title)
            return updated.title

        return conversation.title
