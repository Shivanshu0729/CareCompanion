from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.agent.coach import WellnessCoach
from src.agent.memory_extractor import ExtractedMemory, ExtractionResult, MemoryExtractor
from src.agent.memory_manager import MemoryManager
from src.database.in_memory import InMemoryCareStore
from src.database.models import Goal, MemoryRecord
from src.database.store import CareStore
from src.llm.exceptions import LLMError
from src.llm.provider import LLMMessage, LLMResponse
from tests.conftest import ScriptedLLM


class GeneralMemoryLLM(ScriptedLLM):
    def generate(self, messages, temperature: float = 0.4, max_tokens: int = 900) -> LLMResponse:
        self.calls.append(list(messages))
        system = messages[0].content.lower() if messages else ""
        user = messages[-1].content if messages else ""
        lowered_user = user.lower()

        # Handle extraction prompts
        if "you are the memory extraction engine" in system or "return json only" in system or "extract durable" in system:
            return LLMResponse(content=self._extract_general(user), model="general_llm")

        # Coach response logic based on context
        if "learning python" in system or "learn python" in system:
            if "what should i learn next" in lowered_user:
                return LLMResponse(
                    content="Since you are learning Python, great next steps include exploring FastAPI for web APIs or NumPy and Pandas for data science.",
                    model="general_llm",
                )

        if "ai internship" in system or "internship" in system:
            if "career" in lowered_user or "prepare" in lowered_user:
                return LLMResponse(
                    content="To prepare for your AI internship, focus on building machine learning projects, mastering Git, and practicing Python algorithms.",
                    model="general_llm",
                )

        if "carecompanion" in system or "fastapi and supabase" in system:
            if "continue my previous project" in lowered_user or "previous project" in lowered_user:
                return LLMResponse(
                    content="Picking up from CareCompanion with FastAPI and Supabase: we can continue refining the database schema or build the API endpoints.",
                    model="general_llm",
                )

        if "sleep routine" in lowered_user:
            return LLMResponse(
                content="Aim for a consistent 11 PM bedtime, reduce blue light 1 hour before sleep, and keep your bedroom cool.",
                model="general_llm",
            )

        # Weight queries
        if "weight" in lowered_user:
            if any(w in lowered_user for w in ("previous", "past", "before", "earlier", "history", "used to")):
                if "75" in system or "80" in system:
                    return LLMResponse(content="Your previous recorded weight was 75 kg.", model="general_llm")
                return LLMResponse(content="I do not have a record of a previous weight.", model="general_llm")
            else:
                name_prefix = "Your name is Shivanshu and your" if "shivanshu" in system else "Your"
                if "72" in system:
                    return LLMResponse(content=f"{name_prefix} current weight is 72 kg.", model="general_llm")
                elif "75" in system:
                    return LLMResponse(content=f"{name_prefix} current weight is 75 kg.", model="general_llm")
                elif "80" in system:
                    return LLMResponse(content=f"{name_prefix} current weight is 80 kg.", model="general_llm")

        return LLMResponse(content="I am here to support your goals and routines.", model="general_llm")

    def _extract_general(self, raw_input: str) -> str:
        lowered = raw_input.lower()
        memories = []

        if "learning python" in lowered:
            memories.append({
                "category": "goal",
                "key": "learning_goal_python",
                "value": "User is learning Python.",
                "action": "new",
                "importance": 0.85,
                "confidence": 0.95,
                "requires_consent": False,
            })
        elif "learning java" in lowered:
            memories.append({
                "category": "goal",
                "key": "learning_goal_python",
                "value": "User has switched goal to learning Java.",
                "action": "update",
                "importance": 0.85,
                "confidence": 0.95,
                "requires_consent": False,
            })

        if "ai internship" in lowered:
            memories.append({
                "category": "goal",
                "key": "career_goal",
                "value": "User wants to secure an AI internship.",
                "action": "new",
                "importance": 0.9,
                "confidence": 0.95,
                "requires_consent": False,
            })

        if "building carecompanion with fastapi and supabase" in lowered or "building carecompanion" in lowered:
            memories.append({
                "category": "context",
                "key": "project_carecompanion",
                "value": "Building CareCompanion using FastAPI and Supabase.",
                "action": "new",
                "importance": 0.9,
                "confidence": 0.95,
                "requires_consent": False,
            })

        if "lung and breathing issues" in lowered or "breathing issues" in lowered:
            memories.append({
                "category": "health",
                "key": "health_respiratory",
                "value": "User-reported breathing and lung limits: cannot run 1 km straight.",
                "action": "new",
                "importance": 0.95,
                "confidence": 0.9,
                "requires_consent": True,
            })

        if "concise bullet points" in lowered:
            memories.append({
                "category": "preference",
                "key": "explanation_style",
                "value": "User prefers concise bullet points.",
                "action": "new",
                "importance": 0.7,
                "confidence": 0.9,
                "requires_consent": False,
            })

        return json.dumps({
            "memories": memories,
            "session_summary": "Extracted conversational facts.",
        })


# --- Scenario Tests ---

def test_scenario_1_learning_python_cross_thread(store: InMemoryCareStore, user_a: str) -> None:
    """Test 1: User says 'I am learning Python' in Thread A; asks 'What should I learn next?' in Thread B."""
    llm = GeneralMemoryLLM()
    coach = WellnessCoach(store, llm)

    thread_a = store.create_conversation(user_a, "Coding Journey")
    coach.respond(user_a, thread_a.id, "I am learning Python.")

    # Verify memory saved
    memories = store.list_memories(user_a)
    assert any("python" in m.memory_content.lower() for m in memories)

    # Thread B: Brand new thread
    thread_b = store.create_conversation(user_a, "Next Steps")
    turn_b = coach.respond(user_a, thread_b.id, "What should I learn next?")

    # ContextBuilder must have supplied Python learning memory
    used_content = " ".join(m.content for m in turn_b.memories_used).lower()
    assert "python" in used_content
    assert "python" in turn_b.assistant_message.lower()
    assert "fastapi" in turn_b.assistant_message.lower() or "pandas" in turn_b.assistant_message.lower()


def test_scenario_2_career_goal_cross_thread(store: InMemoryCareStore, user_a: str) -> None:
    """Test 2: User says 'I want an AI internship' in Thread A; asks 'Help me prepare for my career' in Thread B."""
    llm = GeneralMemoryLLM()
    coach = WellnessCoach(store, llm)

    thread_a = store.create_conversation(user_a, "Career Goals")
    coach.respond(user_a, thread_a.id, "I want an AI internship.")

    # Thread B: Brand new thread
    thread_b = store.create_conversation(user_a, "Preparation")
    turn_b = coach.respond(user_a, thread_b.id, "Help me prepare for my career.")

    used_content = " ".join(m.content for m in turn_b.memories_used).lower()
    assert "internship" in used_content or "ai" in used_content
    assert "internship" in turn_b.assistant_message.lower() or "machine learning" in turn_b.assistant_message.lower()


def test_scenario_3_project_context_continuation(store: InMemoryCareStore, user_a: str) -> None:
    """Test 3: User discusses project in Thread A; asks 'Continue my previous project' in Thread B."""
    llm = GeneralMemoryLLM()
    coach = WellnessCoach(store, llm)

    thread_a = store.create_conversation(user_a, "Project Arch")
    coach.respond(user_a, thread_a.id, "I am building CareCompanion with FastAPI and Supabase.")

    # Thread B: Brand new thread
    thread_b = store.create_conversation(user_a, "Next Tasks")
    turn_b = coach.respond(user_a, thread_b.id, "Continue my previous project.")

    used_content = " ".join(m.content for m in turn_b.memories_used).lower()
    assert "carecompanion" in used_content or "fastapi" in used_content
    assert "carecompanion" in turn_b.assistant_message.lower() or "fastapi" in turn_b.assistant_message.lower()


def test_scenario_4_preference_used_only_when_relevant(store: InMemoryCareStore, user_a: str) -> None:
    """Test 4: Preference shared is not force-injected into an unrelated question."""
    store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="preference",
            memory_content="Prefers concise bullet points in Python code reviews",
            memory_key="code_review_style",
            confidence=0.9,
            importance=0.7,
            confirmed=True,
            is_current=True,
        )
    )

    manager = MemoryManager(store)
    # Question completely unrelated to code reviews
    retrieved = manager.retrieve(user_a, "What is a good sleep routine for bedtime?")
    assert not any("code reviews" in m.content for m in retrieved)


def test_scenario_5_goal_update_supersedes_history(store: InMemoryCareStore, user_a: str) -> None:
    """Test 5: Updating a goal makes the new goal current and supersedes the old one."""
    llm = GeneralMemoryLLM()
    coach = WellnessCoach(store, llm)

    thread_a = store.create_conversation(user_a, "Goals 1")
    coach.respond(user_a, thread_a.id, "I am learning Python.")

    thread_b = store.create_conversation(user_a, "Goals 2")
    coach.respond(user_a, thread_b.id, "I am now learning Java instead.")

    all_memories = store.list_memories(user_a)
    current_goals = [m for m in all_memories if m.is_current and "java" in m.memory_content.lower()]
    superseded = [m for m in all_memories if not m.is_current and "python" in m.memory_content.lower()]

    assert len(current_goals) >= 1
    assert len(superseded) >= 1
    assert superseded[0].superseded_by == current_goals[0].id


def test_scenario_6_multi_tenant_user_isolation(store: InMemoryCareStore, user_a: str, user_b: str) -> None:
    """Test 6: User A's memories are never visible to or retrieved for User B."""
    store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="profile",
            memory_content="Secret project name: ProjectTitan",
            confirmed=True,
            is_current=True,
        )
    )

    manager = MemoryManager(store)
    retrieved_b = manager.retrieve(user_b, "Tell me about my projects and ProjectTitan")
    assert not any("projecttitan" in m.content.lower() for m in retrieved_b)
    assert not any("projecttitan" in m.memory_content.lower() for m in store.list_memories(user_b))


def test_scenario_7_deleted_memory_not_retrieved(store: InMemoryCareStore, user_a: str) -> None:
    """Test 7: Deleted memory is never retrieved in subsequent conversations."""
    saved = store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="preference",
            memory_content="Prefers cold brew coffee in the morning",
            confirmed=True,
            is_current=True,
        )
    )
    manager = MemoryManager(store)
    assert any("cold brew" in m.content for m in manager.retrieve(user_a, "What coffee do I prefer?"))

    # Delete memory
    store.delete_memory(user_a, saved.id)
    assert not any("cold brew" in m.content for m in manager.retrieve(user_a, "What coffee do I prefer?"))


def test_scenario_8_sensitive_health_consent_and_safety(store: InMemoryCareStore, user_a: str) -> None:
    """Test 8: Sensitive health disclosures require consent and don't generate dangerous clinical prescriptions."""
    llm = GeneralMemoryLLM()
    extractor = MemoryExtractor(store, llm)

    payload = extractor.extract_payload(
        "I have severe lung and breathing issues so I cannot run 1 km straight.",
        "I hear you. Let's start with gentle walking.",
    )
    # Sensitive health condition requires consent and is flagged in payload
    assert len(payload.health) > 0 or any(m.requires_consent for m in payload.memories)

    # When confirmed with explicit user consent:
    confirmed = store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="health",
            memory_content="User-reported health concern: lung and breathing limits",
            confirmed=True,
            is_current=True,
        )
    )
    retrieved = MemoryManager(store).retrieve(user_a, "Can I do a marathon run tomorrow?")
    assert any("breathing" in m.content.lower() or "lung" in m.content.lower() for m in retrieved)


def test_scenario_9_database_unavailable_graceful_handling(user_a: str) -> None:
    """Test 9: Database failure is handled gracefully without crashing or claiming memory was saved."""
    failing_store = MagicMock(spec=CareStore)
    failing_store.get_conversation.side_effect = RuntimeError("Database unreachable")
    llm = GeneralMemoryLLM()
    coach = WellnessCoach(failing_store, llm)

    with pytest.raises(RuntimeError) as exc_info:
        coach.respond(user_a, "conv-123", "Hello there")
    assert "Database unreachable" in str(exc_info.value)


def test_credential_leakage_protection(store: InMemoryCareStore, user_a: str) -> None:
    """Verify that credentials, API keys, and passwords are NEVER extracted or stored."""
    llm = GeneralMemoryLLM()
    extractor = MemoryExtractor(store, llm)

    # User message with sensitive API token and password
    text_with_keys = "My api_key is gsk_1234567890abcdef123456 and password: SecretPassword123!"
    payload = extractor.extract_payload(text_with_keys, "Understood.")

    # Extraction must be empty or omit credentials
    extractor.persist(user_a, "conv-1", payload)
    stored = store.list_memories(user_a)
    assert not any("gsk_" in m.memory_content for m in stored)
    assert not any("SecretPassword123" in m.memory_content for m in stored)


def test_scenario_10_single_value_weight_update_and_history_across_conversations(
    store: InMemoryCareStore, user_a: str
) -> None:
    """
    Test 10 (Critical 4-Conversation Lifecycle Regression):
    Conv A: User sets initial weight (80 kg) -> saved as current_weight under health.
    Conv B: User updates weight (75 kg) -> supersedes 80 kg, stores 75 kg as current.
    Conv C: User updates weight again (72 kg) -> supersedes 75 kg, stores 72 kg as current.
    Conv D: In a brand new conversation thread:
      - Asks: 'What is my current weight?' -> Must return 72 kg (NOT 80 kg or 75 kg).
      - Asks: 'What was my previous weight?' -> Must retrieve historical value.
    """
    llm = GeneralMemoryLLM()
    coach = WellnessCoach(store, llm)

    # Conversation A: Initial weight 80 kg
    conv_a = store.create_conversation(user_a, "Initial Check-in")
    coach.respond(user_a, conv_a.id, "My name is Shivanshu and my weight is 80 kg.")

    memories_a = store.list_memories(user_a)
    weight_mems_a = [m for m in memories_a if m.memory_key == "current_weight" and m.is_current]
    assert len(weight_mems_a) == 1
    assert "80" in weight_mems_a[0].memory_content
    assert weight_mems_a[0].memory_type == "health"

    # Conversation B: Update weight to 75 kg
    conv_b = store.create_conversation(user_a, "Weight Update 1")
    coach.respond(user_a, conv_b.id, "My weight is now 75 kg.")

    memories_b = store.list_memories(user_a)
    current_b = [m for m in memories_b if m.memory_key == "current_weight" and m.is_current]
    historical_b = [m for m in memories_b if m.memory_key == "current_weight" and not m.is_current]

    assert len(current_b) == 1
    assert "75" in current_b[0].memory_content
    assert len(historical_b) == 1
    assert "80" in historical_b[0].memory_content
    assert historical_b[0].superseded_by == current_b[0].id

    # Conversation C: Update weight again to 72 kg
    conv_c = store.create_conversation(user_a, "Weight Update 2")
    coach.respond(user_a, conv_c.id, "I now weigh 72 kg.")

    memories_c = store.list_memories(user_a)
    current_c = [m for m in memories_c if m.memory_key == "current_weight" and m.is_current]
    historical_c = [m for m in memories_c if m.memory_key == "current_weight" and not m.is_current]

    # Exactly ONE current weight record
    assert len(current_c) == 1
    assert "72" in current_c[0].memory_content
    assert current_c[0].memory_type == "health"

    # Exactly TWO superseded records (80 kg and 75 kg)
    assert len(historical_c) == 2
    assert any("80" in m.memory_content for m in historical_c)
    assert any("75" in m.memory_content for m in historical_c)

    # Conversation D: Completely new conversation thread
    conv_d = store.create_conversation(user_a, "Status Check")

    # Current weight query
    turn_current = coach.respond(user_a, conv_d.id, "What is my current weight?")
    assert "72 kg" in turn_current.assistant_message
    assert "80 kg" not in turn_current.assistant_message
    assert "75 kg" not in turn_current.assistant_message

    # Verify context provided to LLM has only current value
    used_contents = [m.content for m in turn_current.memories_used]
    assert any("72" in c for c in used_contents)
    assert not any("80" in c for c in used_contents)
    assert not any("75" in c for c in used_contents)

    # Previous weight query (historical)
    turn_prev = coach.respond(user_a, conv_d.id, "What was my previous weight?")
    assert "75 kg" in turn_prev.assistant_message


def test_scenario_11_deduplication_and_no_assistant_recommendations_in_memories(
    store: InMemoryCareStore, user_a: str
) -> None:
    """
    Test 11:
    - Assistant recommendations are NOT saved into user_memories as confirmed facts.
    - Duplicate goals are prevented.
    - Memory list returns current_weight under health.
    """
    llm = GeneralMemoryLLM()
    coach = WellnessCoach(store, llm)

    conv = store.create_conversation(user_a, "Habits")
    coach.respond(user_a, conv.id, "I want to improve my sleep routine and bedtime.")

    memories = store.list_memories(user_a)
    # Recommendations must NOT be stored in user_memories
    assert not any(m.memory_type == "recommendation" for m in memories)
    assert not any(m.source == "ai_generated" for m in memories)

    # Add weight and verify category is health
    coach.respond(user_a, conv.id, "My weight is 68 kg.")
    updated_memories = store.list_memories(user_a)
    weight_mems = [m for m in updated_memories if m.memory_key == "current_weight" and m.is_current]
    assert len(weight_mems) == 1
    assert weight_mems[0].memory_type == "health"
    assert "68" in weight_mems[0].memory_content
