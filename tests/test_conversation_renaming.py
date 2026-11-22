from __future__ import annotations

import pytest

from src.agent.coach import WellnessCoach
from src.database.in_memory import InMemoryCareStore
from src.database.models import Message
from src.llm.exceptions import LLMConnectionError, LLMTimeoutError
from src.llm.provider import LLMMessage, LLMResponse
from src.services.conversation_service import ConversationService
from src.services.title_generator import (
    DISALLOWED_TITLES,
    TitleGenerator,
    clean_title,
    generate_fallback_title,
)
from tests.conftest import ScriptedLLM


class MockLLMForTitles:
    """Mock LLM to test title generation with various responses."""

    def __init__(self, response_text: str = "", raise_error: Exception | None = None) -> None:
        self.response_text = response_text
        self.raise_error = raise_error
        self.calls: list[list[LLMMessage]] = []

    def generate(self, messages, temperature: float = 0.2, max_tokens: int = 25) -> LLMResponse:
        self.calls.append(list(messages))
        if self.raise_error:
            raise self.raise_error
        return LLMResponse(content=self.response_text, model="mock")

    def stream_generate(self, messages, temperature: float = 0.2, max_tokens: int = 25):
        resp = self.generate(messages, temperature=temperature, max_tokens=max_tokens)
        yield resp.content


def test_clean_title_removes_quotes_markdown_and_prefixes():
    assert clean_title('"Improving Sleep Schedule"') == "Improving Sleep Schedule"
    assert clean_title("Title: Weight Loss Nutrition.") == "Weight Loss Nutrition"
    assert clean_title("**Building a Workout Routine**") == "Building a Workout Routine"
    assert clean_title("Topic: `Sleep Data Analysis`!") == "Sleep Data Analysis"
    assert clean_title("Understanding Daily Fatigue...") == "Understanding Daily Fatigue"


def test_clean_title_enforces_word_limit():
    long_title = "This is a very long title that contains way too many words to be good"
    cleaned = clean_title(long_title)
    words = cleaned.split()
    assert len(words) <= 6
    assert cleaned == "This is a Very Long Title"


def test_generate_fallback_title_examples():
    # Prompt example 1: I want to improve my sleep schedule
    t1 = generate_fallback_title("I want to improve my sleep schedule")
    assert t1 == "Improving Sleep Schedule"

    # Prompt example 2: What should I eat to lose weight?
    t2 = generate_fallback_title("What should I eat to lose weight?")
    assert t2 == "Weight Loss Nutrition"

    # Prompt example 3: I have been feeling tired recently
    t3 = generate_fallback_title("I have been feeling tired recently")
    assert t3 == "Understanding Daily Fatigue"

    # Prompt example 4: Help me build a consistent workout routine
    t4 = generate_fallback_title("Help me build a consistent workout routine")
    assert t4 == "Building a Workout Routine"

    # Prompt example 5: Analyze my sleep data
    t5 = generate_fallback_title("Analyze my sleep data")
    assert t5 == "Sleep Data Analysis"

    # Prompt example 6: I want to improve my daily activity
    t6 = generate_fallback_title("I want to improve my daily activity")
    assert t6 == "Improving Daily Activity"


def test_generate_fallback_title_short_and_empty():
    assert generate_fallback_title("") == "Getting Started"
    assert generate_fallback_title("   ") == "Getting Started"
    assert generate_fallback_title("hi") in {"Getting Started", "General Inquiry"}
    assert generate_fallback_title("hello there") in {"Getting Started", "General Inquiry", "Hello There"}


def test_title_generator_uses_llm_when_available():
    llm = MockLLMForTitles(response_text='"Improving Sleep Schedule"')
    generator = TitleGenerator(llm)
    title = generator.generate_title("I want to sleep better")
    assert title == "Improving Sleep Schedule"
    assert len(llm.calls) == 1
    # Check that system prompt matches instruction
    system_prompt = llm.calls[0][0].content
    assert "conversation title generator" in system_prompt.lower()
    assert "2–6 words" in system_prompt or "2-6 words" in system_prompt


def test_title_generator_rejects_generic_titles_from_llm():
    # LLM returns generic disallowed title
    llm = MockLLMForTitles(response_text="New conversation")
    generator = TitleGenerator(llm)
    # Should fall back to smart algorithmic title
    title = generator.generate_title("I want to improve my sleep schedule")
    assert title == "Improving Sleep Schedule"


def test_title_generator_handles_llm_error_gracefully():
    llm = MockLLMForTitles(raise_error=LLMConnectionError("Could not reach Groq"))
    generator = TitleGenerator(llm)
    # Does not throw, returns sensible fallback
    title = generator.generate_title("Help me build a consistent workout routine")
    assert title == "Building a Workout Routine"


def test_first_message_renames_conversation_in_coach(store: InMemoryCareStore, llm: ScriptedLLM, user_a: str):
    coach = WellnessCoach(store, llm)
    conv = store.create_conversation(user_a, "New conversation")
    assert conv.title == "New conversation"

    turn = coach.respond(user_a, conv.id, "I want to improve my sleep schedule")
    assert turn.conversation_title == "Improving Sleep Schedule"

    # Verify persisted in database
    saved = store.get_conversation(user_a, conv.id)
    assert saved is not None
    assert saved.title == "Improving Sleep Schedule"


def test_subsequent_messages_do_not_change_title(store: InMemoryCareStore, llm: ScriptedLLM, user_a: str):
    coach = WellnessCoach(store, llm)
    conv = store.create_conversation(user_a, "New conversation")

    # First message renames
    coach.respond(user_a, conv.id, "I want to improve my sleep schedule")
    assert store.get_conversation(user_a, conv.id).title == "Improving Sleep Schedule"

    # Send 10 additional messages with different topics
    topics = [
        "What should I eat for dinner?",
        "How many steps should I walk?",
        "Can you help me with python code?",
        "I feel a bit stressed today",
        "Let's review my workout routine",
        "How much water to drink?",
        "Tell me about vitamins",
        "Can we plan for the weekend?",
        "My heart rate was 72 bpm today",
        "Thank you for the advice!",
    ]
    for topic in topics:
        turn = coach.respond(user_a, conv.id, topic)
        assert turn.conversation_title == "Improving Sleep Schedule"
        assert store.get_conversation(user_a, conv.id).title == "Improving Sleep Schedule"


def test_user_manually_renamed_conversation_is_preserved(store: InMemoryCareStore, llm: ScriptedLLM, user_a: str):
    service = ConversationService(store, llm=llm)
    conv = service.create(user_a, "New conversation")

    # User manually renames BEFORE first message
    service.rename(user_a, conv.id, "My Custom Health Goal")
    assert store.get_conversation(user_a, conv.id).title == "My Custom Health Goal"

    # Now send first message
    coach = WellnessCoach(store, llm)
    turn = coach.respond(user_a, conv.id, "I want to improve my sleep schedule")

    # Title must NOT be overwritten
    assert turn.conversation_title == "My Custom Health Goal"
    assert store.get_conversation(user_a, conv.id).title == "My Custom Health Goal"


def test_two_conversations_created_simultaneously_do_not_conflict(
    store: InMemoryCareStore, llm: ScriptedLLM, user_a: str
):
    coach = WellnessCoach(store, llm)
    conv1 = store.create_conversation(user_a, "New conversation")
    conv2 = store.create_conversation(user_a, "New conversation")

    coach.respond(user_a, conv1.id, "I want to improve my sleep schedule")
    coach.respond(user_a, conv2.id, "Analyze my sleep data")

    assert store.get_conversation(user_a, conv1.id).title == "Improving Sleep Schedule"
    assert store.get_conversation(user_a, conv2.id).title == "Sleep Data Analysis"


def test_stream_respond_renames_conversation_on_first_message(
    store: InMemoryCareStore, llm: ScriptedLLM, user_a: str
):
    coach = WellnessCoach(store, llm)
    conv = store.create_conversation(user_a, "New conversation")

    chunks = list(coach.stream_respond(user_a, conv.id, "I have been feeling tired recently"))
    assert len(chunks) > 0

    saved = store.get_conversation(user_a, conv.id)
    assert saved is not None
    assert saved.title == "Understanding Daily Fatigue"


def test_send_message_api_returns_conversation_title(monkeypatch, user_a: str):
    from api.deps import CurrentUser
    from api.routes.care import MessageCreate, send_message
    from src.database.in_memory import InMemoryCareStore

    store = InMemoryCareStore()
    conv = store.create_conversation(user_a, "New conversation")

    mock_user = CurrentUser(id=user_a, email="user@example.com", client=None)
    monkeypatch.setattr("api.routes.care._store", lambda user: store)
    monkeypatch.setattr("api.routes.care.GroqClient", lambda: ScriptedLLM())

    resp = send_message(
        conversation_id=conv.id,
        body=MessageCreate(content="I want to improve my sleep schedule"),
        user=mock_user,
    )

    assert resp["conversation_title"] == "Improving Sleep Schedule"
    assert resp["conversation_id"] == conv.id
    assert "assistant_message" in resp
    assert store.get_conversation(user_a, conv.id).title == "Improving Sleep Schedule"

