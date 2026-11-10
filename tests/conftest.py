from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.database.in_memory import InMemoryCareStore
from src.llm.provider import LLMResponse

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "pmdata"


class ScriptedLLM:
    def __init__(self) -> None:
        self.calls: list[list] = []

    def generate(self, messages, temperature: float = 0.4, max_tokens: int = 900) -> LLMResponse:
        self.calls.append(list(messages))
        system = messages[0].content.lower() if messages else ""
        user = messages[-1].content if messages else ""
        if "return json only" in system or "extract durable" in system:
            return LLMResponse(content=self._extraction(user), model="scripted")
        return LLMResponse(content=self._coach(system, user), model="scripted")

    def _extraction(self, raw: str) -> str:
        lowered = raw.lower()
        preferences = []
        if "shivanshu" in lowered:
            preferences.append({"content": "User's name is Shivanshu."})
        if "80 kg" in lowered:
            preferences.append({"content": "User's weight is 80 kg."})
        elif "70 kg" in lowered:
            preferences.append({"content": "User's weight is 70 kg."})
        elif "70 kilograms" in lowered:
            preferences.append({"content": "User's weight is 70 kilograms."})
        if preferences:
            return json.dumps(
                {
                    "goals": [],
                    "preferences": preferences,
                    "obstacles": [],
                    "recommendations": [],
                    "commitments": [],
                    "outcomes": [],
                    "session_summary": "",
                }
            )
        if "inconsistent sleep" in lowered or "improve my sleep routine" in lowered:
            return json.dumps(
                {
                    "goals": [{"description": "Improve sleep routine and consistency", "status": "active"}],
                    "preferences": [{"content": "Prefers gradual and realistic recommendations"}],
                    "obstacles": [],
                    "recommendations": [
                        {"text": "Try a consistent 11 PM bedtime with a 30-minute wind-down.", "goal_hint": "sleep"}
                    ],
                    "commitments": [],
                    "outcomes": [],
                    "session_summary": "User wants a more consistent sleep routine. Suggested a gradual 11 PM bedtime.",
                }
            )
        if "managed to maintain" in lowered or "more consistent bedtime" in lowered:
            return json.dumps(
                {
                    "goals": [],
                    "preferences": [],
                    "obstacles": [],
                    "recommendations": [
                        {
                            "text": "Keep the current bedtime window and review it after another week.",
                            "goal_hint": "sleep",
                        }
                    ],
                    "commitments": [],
                    "outcomes": [
                        {
                            "reported_outcome": "Maintained a more consistent bedtime for the last few days",
                            "commitment_hint": "bedtime",
                        }
                    ],
                    "session_summary": "User reported several days of a more consistent bedtime. Next step is to maintain it.",
                }
            )
        if "could not maintain" in lowered or "could not maintain it" in lowered or "11 pm" in lowered:
            return json.dumps(
                {
                    "goals": [],
                    "preferences": [],
                    "obstacles": [
                        {
                            "description": "Could not maintain an 11 PM bedtime",
                            "goal_hint": "sleep",
                        }
                    ],
                    "recommendations": [
                        {
                            "text": "Shift bedtime later by 15 minutes and keep the wind-down ritual.",
                            "goal_hint": "sleep",
                        }
                    ],
                    "commitments": [{"description": "Will try a later, more realistic bedtime"}],
                    "outcomes": [],
                    "session_summary": "User could not keep 11 PM. Plan adjusted to a more gradual shift.",
                }
            )
        return json.dumps(
            {
                "goals": [],
                "preferences": [],
                "obstacles": [],
                "recommendations": [],
                "commitments": [],
                "outcomes": [],
                "session_summary": "",
            }
        )

    def _coach(self, system: str, user: str) -> str:
        lowered = user.lower()
        if "could not maintain" in lowered:
            if "improve sleep" in system or "sleep routine" in system:
                return (
                    "I remember your goal to improve sleep consistency. Since 11 PM was too early to maintain, "
                    "let's adjust to a later, more realistic wind-down instead of forcing that clock time."
                )
            return "Let's adjust the previous bedtime plan because it was too difficult to keep."
        if "managed to maintain" in lowered:
            return (
                "You previously wanted a more consistent sleep routine and reported that 11 PM was too strict. "
                "Now that a more consistent bedtime has been easier to keep, we should protect that window rather than adding a harder target."
            )
        if "inconsistent sleep" in lowered or "improve my sleep" in lowered:
            return "A realistic first step is a consistent sleep wind-down and an 11 PM target only if it fits your evenings."
        return "I can help with sleep, activity and wellness goals using your saved history when it is relevant."


@pytest.fixture
def store() -> InMemoryCareStore:
    return InMemoryCareStore()


@pytest.fixture
def llm() -> ScriptedLLM:
    return ScriptedLLM()


@pytest.fixture
def user_a() -> str:
    return "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def user_b() -> str:
    return "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def pmdata_fixture_root() -> Path:
    return FIXTURE_ROOT


def write_pmdata_fixture(root: Path) -> None:
    fitbit = root / "p01" / "fitbit"
    fitbit.mkdir(parents=True, exist_ok=True)
    days = pd.date_range("2019-11-01", periods=10, freq="D")
    daily = [{"dateTime": f"{day.date()} 00:00:00", "value": str(600 + i * 10)} for i, day in enumerate(days)]
    (fitbit / "sedentary_minutes.json").write_text(json.dumps(daily), encoding="utf-8")
    light = [{"dateTime": f"{day.date()} 00:00:00", "value": str(180 + i)} for i, day in enumerate(days)]
    (fitbit / "lightly_active_minutes.json").write_text(json.dumps(light), encoding="utf-8")
    moderate = [{"dateTime": f"{day.date()} 00:00:00", "value": str(20 + i)} for i, day in enumerate(days)]
    (fitbit / "moderately_active_minutes.json").write_text(json.dumps(moderate), encoding="utf-8")
    very = [{"dateTime": f"{day.date()} 00:00:00", "value": str(15 + i)} for i, day in enumerate(days)]
    (fitbit / "very_active_minutes.json").write_text(json.dumps(very), encoding="utf-8")
    rhr = [
        {
            "dateTime": f"{day.date()} 00:00:00",
            "value": {"date": day.strftime("%m/%d/%y"), "value": 52.0 + i * 0.2, "error": 6.7},
        }
        for i, day in enumerate(days)
    ]
    (fitbit / "resting_heart_rate.json").write_text(json.dumps(rhr), encoding="utf-8")
    steps = []
    for i, day in enumerate(days):
        for hour in range(3):
            steps.append({"dateTime": f"{day.date()} {hour:02d}:00:00", "value": str(1000 + i + hour)})
    (fitbit / "steps.json").write_text(json.dumps(steps), encoding="utf-8")
    sleep = [
        {
            "logId": 1000 + i,
            "dateOfSleep": str(day.date()),
            "startTime": f"{day.date()} 00:10:00",
            "endTime": f"{day.date()} 07:10:00",
            "duration": 25200000,
            "minutesAsleep": 380 + i,
            "timeInBed": 420,
            "efficiency": 90,
            "type": "stages",
        }
        for i, day in enumerate(days)
    ]
    (fitbit / "sleep.json").write_text(json.dumps(sleep), encoding="utf-8")
    score_lines = [
        "timestamp,sleep_log_entry_id,overall_score,composition_score,revitalization_score,duration_score,deep_sleep_in_minutes,resting_heart_rate,restlessness"
    ]
    for i, day in enumerate(days):
        score_lines.append(
            f"{day.date()}T07:00:00Z,{2000 + i},70,18,20,38,{30 + i},52,0.08"
        )
    (fitbit / "sleep_score.csv").write_text("\n".join(score_lines), encoding="utf-8")
