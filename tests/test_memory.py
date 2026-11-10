from __future__ import annotations

import json

from src.agent.memory_extractor import MemoryExtractor
from src.agent.memory_manager import MemoryManager
from src.database.models import Goal, MemoryRecord, Obstacle, Recommendation
from src.database.in_memory import InMemoryCareStore
from tests.conftest import ScriptedLLM


class HealthMemoryLLM(ScriptedLLM):
    def _extraction(self, raw: str) -> str:
        return json.dumps(
            {
                "goals": [],
                "preferences": [],
                "obstacles": [],
                "recommendations": [],
                "commitments": [],
                "outcomes": [],
                "health": [{"concern": "cancer, reported by the user"}],
                "session_summary": "",
            }
        )


def test_store_and_update_memory(store: InMemoryCareStore, user_a: str) -> None:
    saved = store.add_memory(
        MemoryRecord(user_id=user_a, memory_type="preference", memory_content="Prefers gradual plans")
    )
    updated = store.update_memory(user_a, saved.id, "Prefers gradual evening plans")
    assert updated.memory_content == "Prefers gradual evening plans"


def test_duplicate_memory_prevention(store: InMemoryCareStore, user_a: str) -> None:
    first = store.add_memory(
        MemoryRecord(user_id=user_a, memory_type="goal", memory_content="Improve sleep consistency")
    )
    second = store.add_memory(
        MemoryRecord(user_id=user_a, memory_type="goal", memory_content="improve sleep consistency")
    )
    assert first.id == second.id
    assert len(store.list_memories(user_a, "goal")) == 1


def test_cross_conversation_retrieval(store: InMemoryCareStore, user_a: str) -> None:
    store.add_goal(Goal(user_id=user_a, goal_description="Improve sleep routine"))
    store.add_recommendation(
        Recommendation(user_id=user_a, recommendation="Try a consistent 11 PM bedtime")
    )
    store.add_obstacle(Obstacle(user_id=user_a, obstacle_description="Could not maintain an 11 PM bedtime"))
    manager = MemoryManager(store)
    retrieved = manager.retrieve(user_a, "How is my sleep progress going?")
    kinds = {item.kind for item in retrieved}
    contents = " ".join(item.content for item in retrieved).lower()
    assert "goal" in kinds
    assert "obstacle" in kinds
    assert "sleep" in contents
    assert "11 pm" in contents or "11" in contents


def test_extractor_persists_goal(store: InMemoryCareStore, llm: ScriptedLLM, user_a: str) -> None:
    conversation = store.create_conversation(user_a, "One")
    extractor = MemoryExtractor(store, llm)
    payload = extractor.extract_payload(
        "I have an inconsistent sleep schedule. I want to improve my sleep routine.",
        "Try 11 PM.",
    )
    extractor.persist(user_a, conversation.id, payload)
    assert store.list_goals(user_a)
    assert store.list_recommendations(user_a)
    assert store.list_session_summaries(user_a)


def test_extractor_persists_name_and_weight(store: InMemoryCareStore, llm: ScriptedLLM, user_a: str) -> None:
    conversation = store.create_conversation(user_a, "Personal details")
    extractor = MemoryExtractor(store, llm)
    payload = extractor.extract_payload("My name is Shivanshu and my weight is 80 kg.", "Thanks.")
    extractor.persist(user_a, conversation.id, payload)

    memories = store.list_memories(user_a, "preference")
    contents = " ".join(item.memory_content for item in memories).lower()
    assert "shivanshu" in contents
    assert "80 kg" in contents

    retrieved = MemoryManager(store).retrieve(user_a, "What is my name and weight?")
    retrieved_contents = " ".join(item.content for item in retrieved).lower()
    assert "shivanshu" in retrieved_contents
    assert "80 kg" in retrieved_contents


def test_extractor_uses_model_output_for_natural_personal_detail_phrasing(
    store: InMemoryCareStore, llm: ScriptedLLM, user_a: str
) -> None:
    conversation = store.create_conversation(user_a, "Updated details")
    extractor = MemoryExtractor(store, llm)
    payload = extractor.extract_payload(
        "You can call me Shivanshu; I currently weigh 70 kilograms.",
        "Thanks, I will use that in future guidance.",
    )
    extractor.persist(user_a, conversation.id, payload)

    contents = " ".join(
        item.memory_content for item in store.list_memories(user_a, "preference")
    ).lower()
    assert "shivanshu" in contents
    assert "70 kilograms" in contents


def test_extractor_requests_consent_for_user_reported_health_concern(
    store: InMemoryCareStore, user_a: str
) -> None:
    conversation = store.create_conversation(user_a, "Health")
    extractor = MemoryExtractor(store, HealthMemoryLLM())
    payload = extractor.extract_payload("I have cancer.", "I will keep this in mind.")
    extractor.persist(user_a, conversation.id, payload)
    assert store.list_memories(user_a, "health") == []
    assert payload.health[0].concern == "cancer, reported by the user"

    store.add_memory(
        MemoryRecord(
            user_id=user_a,
            conversation_id=conversation.id,
            memory_type="health",
            memory_content="User-reported health concern: cancer, reported by the user",
            confirmed=True,
        )
    )
    memories = store.list_memories(user_a, "health")
    assert len(memories) == 1
    retrieved = MemoryManager(store).retrieve(user_a, "What should I consider for my health?")
    assert any("cancer" in item.content.lower() for item in retrieved)


def test_memory_update_keeps_previous_value_as_history(store: InMemoryCareStore, user_a: str) -> None:
    first = store.add_memory(
        MemoryRecord(
            user_id=user_a,
            memory_type="preference",
            memory_content="User's weight is 80 kg.",
            memory_key="weight",
        )
    )
    current = store.update_memory(user_a, first.id, "User's weight is 78 kg.")

    assert current.is_current is True
    assert store.memories[first.id].is_current is False
    assert store.memories[first.id].superseded_by == current.id
    retrieved = MemoryManager(store).retrieve(user_a, "What is my current weight?")
    assert any("78 kg" in item.content for item in retrieved)
    assert not any("80 kg" in item.content for item in retrieved)


def test_weight_update_is_used_in_a_new_profile_conversation(
    store: InMemoryCareStore, user_a: str, user_b: str, llm: ScriptedLLM
) -> None:
    first = store.create_conversation(user_a, "First chat")
    second = store.create_conversation(user_a, "Second chat")
    extractor = MemoryExtractor(store, llm)
    extractor.persist(user_a, first.id, extractor.extract_payload("My weight is 80 kg.", "Saved."))
    extractor.persist(user_a, second.id, extractor.extract_payload("My weight is now 70 kg.", "Updated."))

    memories = store.list_memories(user_a, "preference")
    current_weights = [item for item in memories if item.memory_key == "weight" and item.is_current]
    assert len(current_weights) == 1
    assert "70 kg" in current_weights[0].memory_content
    assert any("80 kg" in item.memory_content and not item.is_current for item in memories)

    profile = MemoryManager(store).retrieve(user_a, "Tell me all about Shivanshu.")
    profile_text = " ".join(item.content for item in profile)
    assert "70 kg" in profile_text
    assert "80 kg" not in profile_text
    assert not MemoryManager(store).retrieve(user_b, "Tell me all about Shivanshu.")


def test_deleting_conversation_deletes_its_memories(store: InMemoryCareStore, user_a: str) -> None:
    conversation = store.create_conversation(user_a, "Private details")
    store.add_memory(
        MemoryRecord(
            user_id=user_a,
            conversation_id=conversation.id,
            memory_type="preference",
            memory_content="User's weight is 80 kg.",
        )
    )
    store.delete_conversation(user_a, conversation.id)
    assert store.list_memories(user_a, "preference") == []

    assert store.list_goals(user_a) == []
