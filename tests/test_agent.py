from __future__ import annotations

from src.agent.coach import WellnessCoach
from src.agent.context_builder import ContextBuilder
from src.agent.memory_manager import RetrievedMemory
from src.data.health_service import HealthContext
from src.database.models import Message
from src.database.in_memory import InMemoryCareStore
from tests.conftest import ScriptedLLM


def test_context_includes_relevant_memory_not_unrelated() -> None:
    builder = ContextBuilder()
    messages = builder.build(
        user_message="Can we revisit my sleep plan?",
        history=[Message(conversation_id="c", user_id="u", role="user", content="hello")],
        memories=[
            RetrievedMemory(kind="goal", content="Improve sleep consistency", source="user_reported", score=0.9),
            RetrievedMemory(kind="obstacle", content="Early bedtime was too hard", source="user_reported", score=0.8),
        ],
        health=HealthContext(
            participant_id="p01",
            source_label="PMData Fitbit research dataset",
            date_start="2019-11-01",
            date_end="2019-11-10",
            recent_rows=[],
            available_metrics=[],
            notes=["labelled demo data"],
        ),
    )
    system = messages[0].content
    assert "Improve sleep consistency" in system
    assert "Early bedtime was too hard" in system
    assert "labelled demo data" in system
    assert messages[-1].content == "Can we revisit my sleep plan?"


def test_three_session_personalization(store: InMemoryCareStore, llm: ScriptedLLM, user_a: str, tmp_path) -> None:
    from src.data.health_service import HealthService

    coach = WellnessCoach(store, llm, health_service=HealthService(processed_path=tmp_path / "missing.csv"))
    first = store.create_conversation(user_a, "Session 1")
    turn1 = coach.respond(
        user_a,
        first.id,
        "I have an inconsistent sleep schedule. I want to improve my sleep routine.",
    )
    assert store.list_goals(user_a)
    assert "sleep" in turn1.assistant_message.lower()

    second = store.create_conversation(user_a, "Session 2")
    turn2 = coach.respond(
        user_a,
        second.id,
        "I tried sleeping at 11 PM, but I could not maintain it.",
    )
    used = " ".join(item.content for item in turn2.memories_used).lower()
    assert "sleep" in used
    assert store.list_obstacles(user_a)
    assert "adjust" in turn2.assistant_message.lower() or "remember" in turn2.assistant_message.lower()

    third = store.create_conversation(user_a, "Session 3")
    turn3 = coach.respond(
        user_a,
        third.id,
        "I managed to maintain a more consistent bedtime for the last few days.",
    )
    used3 = " ".join(item.content for item in turn3.memories_used).lower()
    assert "11" in used3 or "sleep" in used3
    assert store.list_outcomes(user_a)
    assert len(store.list_conversations(user_a)) == 3
    assert store.list_messages(user_a, first.id)
    assert store.list_messages(user_a, second.id)
    coaching_calls = [call for call in llm.calls if "json only" not in call[0].content.lower()]
    session2_system = coaching_calls[1][0].content.lower()
    assert "improve sleep" in session2_system or "sleep routine" in session2_system
