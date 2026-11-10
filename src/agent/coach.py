from __future__ import annotations

from dataclasses import dataclass, field

from src.agent.context_builder import ContextBuilder
from src.agent.memory_extractor import ExtractionResult, MemoryExtractor
from src.agent.memory_manager import MemoryManager, RetrievedMemory
from src.agent.response_validator import ResponseValidator
from src.data.health_service import HealthContext, HealthService
from src.database.store import CareStore
from src.llm.exceptions import LLMError
from src.llm.prompts import (
    build_title_from_message,
    is_meal_plan_request,
    meal_plan_is_complete,
)
from src.llm.provider import LLMMessage, LLMProvider
from src.services.conversation_service import ConversationService


@dataclass
class CoachTurn:
    assistant_message: str
    memories_used: list[RetrievedMemory] = field(default_factory=list)
    health_used: HealthContext | None = None
    extraction: ExtractionResult | None = None
    conversation_id: str = ""


class WellnessCoach:
    def __init__(
        self,
        store: CareStore,
        llm: LLMProvider,
        health_service: HealthService | None = None,
        max_history: int = 12,
        max_memories: int = 12,
    ) -> None:
        self.store = store
        self.llm = llm
        self.health_service = health_service or HealthService()
        self.conversations = ConversationService(store)
        self.memory_manager = MemoryManager(store)
        self.extractor = MemoryExtractor(store, llm)
        self.context_builder = ContextBuilder()
        self.validator = ResponseValidator()
        self.max_history = max_history
        self.max_memories = max_memories

    def respond(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
    ) -> CoachTurn:
        text = user_message.strip()
        if not text:
            raise ValueError("Enter a message before sending.")
        conversation = self.store.get_conversation(user_id, conversation_id)
        if conversation is None:
            raise KeyError("Conversation not found.")
        history = self.store.list_messages(user_id, conversation_id, limit=self.max_history)
        memories = self.memory_manager.retrieve(user_id, text, limit=self.max_memories)
        participant_id = self.memory_manager.demo_participant(user_id)
        health = self.health_service.context_for_query(participant_id, text)
        prompt = self.context_builder.build(
            user_message=text,
            history=history,
            memories=memories,
            health=health,
            max_history=self.max_history,
        )
        try:
            meal_plan = is_meal_plan_request(text)
            output_limit = 1800 if meal_plan else 350
            llm_response = self.llm.generate(
                prompt,
                temperature=0.3,
                max_tokens=output_limit,
            )
            if meal_plan and (
                llm_response.finish_reason == "length"
                or not meal_plan_is_complete(llm_response.content)
            ):
                retry_prompt = prompt + [
                    LLMMessage(
                        role="user",
                        content=(
                            "Your previous draft was incomplete. Return the complete final answer now: "
                            "exactly seven rows Monday through Sunday, with populated Breakfast, Lunch, "
                            "Snack, and Dinner cells, followed by Hydration, Activity, and a safety note. "
                            "Do not shorten it or ask to continue."
                        ),
                    )
                ]
                llm_response = self.llm.generate(
                    retry_prompt,
                    temperature=0.2,
                    max_tokens=3000,
                )
            content = self.validator.validate(
                llm_response,
                health_available=bool(health.recent_rows),
            )
            if meal_plan and not meal_plan_is_complete(content):
                raise LLMError(
                    "The meal plan response was incomplete. Please send the request again."
                )
        except LLMError:
            raise
        self.store.add_message(user_id, conversation_id, "user", text)
        self.store.add_message(user_id, conversation_id, "assistant", content)
        if conversation.title in {"New conversation", "New Conversation"}:
            self.conversations.rename(user_id, conversation_id, build_title_from_message(text))
        extraction = None
        try:
            extraction = self.extractor.extract_payload(text, content)
            self.extractor.persist(user_id, conversation_id, extraction)
        except LLMError:
            extraction = ExtractionResult(session_summary="")
        return CoachTurn(
            assistant_message=content,
            memories_used=memories,
            health_used=health,
            extraction=extraction,
            conversation_id=conversation_id,
        )
