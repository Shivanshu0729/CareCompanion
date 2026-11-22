from __future__ import annotations

import pytest

from src.agent.coach import WellnessCoach
from src.data.health_service import HealthService
from src.database.in_memory import InMemoryCareStore
from src.database.models import UserProfile, MemoryRecord
from src.services.conversation_service import ConversationService
from src.services.single_user_guard import (
    THIRD_PARTY_REFUSAL_MESSAGE,
    OFF_TOPIC_HEALTH_REDIRECT,
    is_third_party_health_request,
    is_off_topic_non_health,
)
from tests.conftest import ScriptedLLM


# -----------------------------------------------------------------------------
# Test A: New account onboarding flow (save_profile / onboarding_completed)
# -----------------------------------------------------------------------------
def test_a_new_account_onboarding_flow(store: InMemoryCareStore, user_a: str) -> None:
    # Initially user has no profile
    initial_profile = store.get_profile(user_a)
    assert initial_profile is None

    # Complete onboarding
    profile_data = UserProfile(
        user_id=user_a,
        full_name="Shivanshu",
        age=26,
        sex="male",
        height=175.0,
        current_weight=78.5,
        unit_preference="metric",
        primary_goal="Improving fitness",
        goals=["Improving fitness", "Better sleep"],
        activity_level="moderately_active",
        dietary_preference="non_vegetarian",
        allergies="None",
        medical_conditions="None",
        sleep_duration_hours=7.5,
        sleep_quality="Good",
        onboarding_completed=True,
    )
    saved = store.save_profile(profile_data)
    assert saved.onboarding_completed is True
    assert saved.user_id == user_a
    assert saved.full_name == "Shivanshu"
    assert saved.current_weight == 78.5

    # Fetch again
    fetched = store.get_profile(user_a)
    assert fetched is not None
    assert fetched.onboarding_completed is True
    assert fetched.full_name == "Shivanshu"


# -----------------------------------------------------------------------------
# Test B: Separate account isolation (User B sees none of User A's data)
# -----------------------------------------------------------------------------
def test_b_separate_account_isolation(
    store: InMemoryCareStore, user_a: str, user_b: str
) -> None:
    # Setup User A profile, conversation, and memories
    profile_a = UserProfile(
        user_id=user_a,
        full_name="User Alpha",
        current_weight=80.0,
        goals=["Weight loss"],
        onboarding_completed=True,
    )
    store.save_profile(profile_a)

    conv_a = store.create_conversation(user_a, "Alpha's Private Chat")
    store.add_message(user_a, conv_a.id, "user", "My private health message")
    store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="health",
            memory_key="current_weight",
            memory_content="User's weight is 80 kg.",
            is_current=True,
        )
    )

    # Verify User B sees none of User A's profile
    profile_b = store.get_profile(user_b)
    assert profile_b is None

    # Verify User B sees none of User A's conversations or messages
    assert store.list_conversations(user_b) == []
    assert store.get_conversation(user_b, conv_a.id) is None
    assert store.list_messages(user_b, conv_a.id) == []

    # Verify User B sees none of User A's memories
    memories_b = store.list_memories(user_b)
    assert len(memories_b) == 0

    # User B creating their own data does not affect User A
    profile_b = UserProfile(
        user_id=user_b,
        full_name="User Beta",
        current_weight=65.0,
        goals=["Better sleep"],
        onboarding_completed=True,
    )
    store.save_profile(profile_b)
    assert store.get_profile(user_a).full_name == "User Alpha"
    assert store.get_profile(user_b).full_name == "User Beta"


# -----------------------------------------------------------------------------
# Test C: Cross-user access protection (reject cross-user access attempts)
# -----------------------------------------------------------------------------
def test_c_cross_user_access_protection(
    store: InMemoryCareStore, user_a: str, user_b: str
) -> None:
    conv_service = ConversationService(store)
    conv_a = conv_service.create(user_a, "Alpha Private Thread")

    mem_a = store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="health",
            memory_content="Alpha secret condition",
        )
    )

    # User B trying to get User A's conversation returns None
    assert conv_service.get(user_b, conv_a.id) is None

    # User B trying to delete User A's conversation raises KeyError
    with pytest.raises(KeyError):
        conv_service.delete(user_b, conv_a.id)

    # User A's conversation is still intact
    assert conv_service.get(user_a, conv_a.id) is not None

    # User B trying to delete User A's memory raises KeyError
    with pytest.raises(KeyError):
        store.delete_memory(user_b, mem_a.id)

    # User A's memory is still intact
    assert store.get_memory(user_a, mem_a.id) is not None


# -----------------------------------------------------------------------------
# Test D: Third-party recommendation refusal & zero memory leakage
# -----------------------------------------------------------------------------
def test_d_third_party_recommendation_refusal(
    store: InMemoryCareStore, llm: ScriptedLLM, user_a: str, tmp_path
) -> None:
    coach = WellnessCoach(
        store,
        llm,
        health_service=HealthService(processed_path=tmp_path / "missing.csv"),
    )
    conv = store.create_conversation(user_a, "Third-party test")

    third_party_queries = [
        "My friend's weight is 100 kg. Suggest a diet for him.",
        "My father has diabetes and high blood pressure. What exercises should he do?",
        "Can you create a meal plan for my girlfriend who wants to lose weight?",
        "What workout should my brother do for his knee injury?",
    ]

    for query in third_party_queries:
        turn = coach.respond(user_a, conv.id, query)
        # Strict exact refusal
        assert turn.assistant_message == THIRD_PARTY_REFUSAL_MESSAGE
        # Guard function identifies it as third party
        is_tp, entity = is_third_party_health_request(query)
        assert is_tp is True
        assert entity is not None

    # Ensure zero third-party memories were extracted or saved
    memories = store.list_memories(user_a)
    mem_texts = " ".join(m.memory_content.lower() for m in memories)
    assert "100 kg" not in mem_texts
    assert "diabetes" not in mem_texts
    assert "girlfriend" not in mem_texts
    assert "brother" not in mem_texts


# -----------------------------------------------------------------------------
# Test E: Self-related coaching is allowed and properly handled
# -----------------------------------------------------------------------------
def test_e_self_coaching_allowed(
    store: InMemoryCareStore, llm: ScriptedLLM, user_a: str, tmp_path
) -> None:
    coach = WellnessCoach(
        store,
        llm,
        health_service=HealthService(processed_path=tmp_path / "missing.csv"),
    )
    conv = store.create_conversation(user_a, "Self coaching")

    self_queries = [
        "Suggest a diet plan for me.",
        "How can I improve my sleep?",
        "What exercises should I do based on my health profile?",
        "My current weight is 80 kg. Help me improve my fitness.",
    ]

    for query in self_queries:
        is_tp, _ = is_third_party_health_request(query)
        assert is_tp is False
        turn = coach.respond(user_a, conv.id, query)
        assert turn.assistant_message != THIRD_PARTY_REFUSAL_MESSAGE


# -----------------------------------------------------------------------------
# Test F: Account switching state isolation (simulating User A -> User B)
# -----------------------------------------------------------------------------
def test_f_account_switching_state_isolation(
    store: InMemoryCareStore, user_a: str, user_b: str
) -> None:
    # User A logs in and creates state
    profile_a = UserProfile(user_id=user_a, full_name="User A", current_weight=75.0, onboarding_completed=True)
    store.save_profile(profile_a)
    conv_a = store.create_conversation(user_a, "User A Chat")
    store.add_memory(
        MemoryRecord(user_id=user_a, memory_type="preference", memory_content="User A prefers oats for breakfast")
    )

    # Simulate logout of User A & login of User B
    # User B should have fresh empty state
    assert store.get_profile(user_b) is None
    assert store.list_conversations(user_b) == []
    assert store.list_memories(user_b) == []

    # User B completes onboarding
    profile_b = UserProfile(user_id=user_b, full_name="User B", current_weight=90.0, onboarding_completed=True)
    store.save_profile(profile_b)
    conv_b = store.create_conversation(user_b, "User B Chat")
    store.add_memory(
        MemoryRecord(user_id=user_b, memory_type="preference", memory_content="User B prefers eggs for breakfast")
    )

    # Check that User A's data was completely unmodified
    assert store.get_profile(user_a).current_weight == 75.0
    mem_a = store.list_memories(user_a)
    assert any("oats" in m.memory_content for m in mem_a)
    assert not any("eggs" in m.memory_content for m in mem_a)

    # Check that User B's data is isolated
    mem_b = store.list_memories(user_b)
    assert any("eggs" in m.memory_content for m in mem_b)
    assert not any("oats" in m.memory_content for m in mem_b)


# -----------------------------------------------------------------------------
# Test G: Memory ownership & update isolation
# -----------------------------------------------------------------------------
def test_g_memory_ownership_and_update_isolation(
    store: InMemoryCareStore, user_a: str, user_b: str
) -> None:
    # User A saves initial weight
    store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="health",
            memory_key="current_weight",
            memory_content="User's weight is 80 kg.",
            is_current=True,
        )
    )

    # User B saves initial weight
    store.add_memory(
        MemoryRecord(
            user_id=user_b,
            memory_type="health",
            memory_key="current_weight",
            memory_content="User's weight is 60 kg.",
            is_current=True,
        )
    )

    # User A updates weight to 82 kg
    store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="health",
            memory_key="current_weight",
            memory_content="User's weight is 82 kg.",
            is_current=True,
        )
    )

    # Active memory for User A is 82 kg
    active_a = [m for m in store.list_memories(user_a) if m.is_current]
    assert len(active_a) == 1
    assert "82 kg" in active_a[0].memory_content

    # Active memory for User B is still 60 kg (unaffected by User A's update)
    active_b = [m for m in store.list_memories(user_b) if m.is_current]
    assert len(active_b) == 1
    assert "60 kg" in active_b[0].memory_content


# -----------------------------------------------------------------------------
# Test H: Health-domain boundary (off-topic non-health tasks redirected)
# -----------------------------------------------------------------------------
def test_h_health_domain_boundary(
    store: InMemoryCareStore, llm: ScriptedLLM, user_a: str, tmp_path
) -> None:
    coach = WellnessCoach(
        store,
        llm,
        health_service=HealthService(processed_path=tmp_path / "missing.csv"),
    )
    conv = store.create_conversation(user_a, "Domain Boundary")

    off_topic_queries = [
        "Write a Python script to scrape a website.",
        "Can you write a JavaScript function for binary search?",
        "Solve this math equation: 3x^2 + 5x - 2 = 0",
        "Write an essay about the causes of World War 2.",
        "Help me debug this Docker Compose error.",
    ]

    for query in off_topic_queries:
        is_off, reason = is_off_topic_non_health(query)
        assert is_off is True
        assert reason is not None
        turn = coach.respond(user_a, conv.id, query)
        assert turn.assistant_message == OFF_TOPIC_HEALTH_REDIRECT
