from __future__ import annotations

from src.agent.context_builder import ContextBuilder
from src.agent.coach import WellnessCoach
from src.data.health_service import HealthContext
from src.database.in_memory import InMemoryCareStore
from src.llm.prompts import is_meal_plan_request, meal_plan_is_complete
from src.llm.provider import LLMResponse


class RecordingLLM:
    def __init__(self) -> None:
        self.max_tokens: list[int] = []

    def generate(self, messages, *, temperature: float = 0.4, max_tokens: int = 900) -> LLMResponse:
        self.max_tokens.append(max_tokens)
        return LLMResponse(
            content=(
                "# 7-Day Meal Plan\n\n"
                "Portions: use a balanced plate and household measures.\n\n"
                "| Day | Breakfast | Lunch | Snack | Dinner |\n"
                "|---|---|---|---|---|\n"
                + "\n".join(
                    f"| {day} | Poha | Dal and roti | Fruit | Vegetable curry |"
                    for day in (
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    )
                )
                + "\n\n### Hydration\nDrink water regularly.\n\n### Activity\nWalk regularly."
            ),
            model="test",
        )


def test_meal_plan_requests_are_detected() -> None:
    assert is_meal_plan_request("Please make me a 7-day diet chart.")
    assert is_meal_plan_request("Can you create a meal plan?")
    assert not is_meal_plan_request("How can I sleep better?")


def test_meal_plan_prompt_requires_structured_chart() -> None:
    messages = ContextBuilder().build(
        user_message="Please make me a 7-day diet chart.",
        history=[],
        memories=[],
        health=HealthContext(
            participant_id="p01",
            source_label="PMData",
            date_start="",
            date_end="",
            recent_rows=[],
            available_metrics=[],
            notes=[],
        ),
    )
    assert "exactly seven days" in messages[0].content
    assert "Breakfast, Lunch, Snack, and Dinner" in messages[0].content


def test_meal_plan_receives_larger_generation_budget() -> None:
    store = InMemoryCareStore()
    llm = RecordingLLM()
    coach = WellnessCoach(store, llm)
    conversation = store.create_conversation("user", "Nutrition")
    turn = coach.respond("user", conversation.id, "Please make me a 7-day diet chart.")
    assert meal_plan_is_complete(turn.assistant_message)
    assert llm.max_tokens == [1800]
