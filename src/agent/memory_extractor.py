from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from src.database.models import (
    Commitment,
    Goal,
    MemoryRecord,
    Obstacle,
    Outcome,
    Recommendation,
    SessionSummary,
)
from src.database.store import CareStore
from src.llm.prompts import MEMORY_EXTRACTION_PROMPT
from src.llm.provider import LLMMessage, LLMProvider
from src.services.text_utils import memory_key, tokenize

logger = logging.getLogger(__name__)

MEMORY_HINTS = {
    "age",
    "allergic",
    "allergy",
    "asthma",
    "cancer",
    "commit",
    "condition",
    "diagnosed",
    "diagnosis",
    "difficult",
    "exercise",
    "goal",
    "health",
    "height",
    "kg",
    "kilograms",
    "medication",
    "medicines",
    "name",
    "obstacle",
    "pounds",
    "prefer",
    "progress",
    "routine",
    "sleep",
    "treatment",
    "want",
    "weigh",
    "weight",
    "will",
    "trying",
}


class ExtractedGoal(BaseModel):
    description: str
    status: str = "active"


class ExtractedPreference(BaseModel):
    content: str


class ExtractedObstacle(BaseModel):
    description: str
    goal_hint: str = ""


class ExtractedRecommendation(BaseModel):
    text: str
    goal_hint: str = ""


class ExtractedCommitment(BaseModel):
    description: str


class ExtractedOutcome(BaseModel):
    reported_outcome: str
    commitment_hint: str = ""


class ExtractedHealth(BaseModel):
    concern: str


class ExtractionResult(BaseModel):
    goals: list[ExtractedGoal] = Field(default_factory=list)
    preferences: list[ExtractedPreference] = Field(default_factory=list)
    obstacles: list[ExtractedObstacle] = Field(default_factory=list)
    recommendations: list[ExtractedRecommendation] = Field(default_factory=list)
    commitments: list[ExtractedCommitment] = Field(default_factory=list)
    outcomes: list[ExtractedOutcome] = Field(default_factory=list)
    health: list[ExtractedHealth] = Field(default_factory=list)
    session_summary: str = ""


JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

class MemoryExtractor:
    def __init__(self, store: CareStore, llm: LLMProvider) -> None:
        self.store = store
        self.llm = llm

    def should_extract(self, user_message: str, assistant_message: str) -> bool:
        combined = f"{user_message} {assistant_message}".lower()
        tokens = tokenize(combined)
        return bool(tokens & MEMORY_HINTS) or "bedtime" in combined

    def extract_payload(self, user_message: str, assistant_message: str) -> ExtractionResult:
        if not self.should_extract(user_message, assistant_message):
            return ExtractionResult()
        prompt_messages = [
            LLMMessage(role="system", content=MEMORY_EXTRACTION_PROMPT),
            LLMMessage(
                role="user",
                content=json.dumps({"user": user_message, "assistant": assistant_message}),
            ),
        ]
        response = self.llm.generate(prompt_messages, temperature=0.0, max_tokens=400)
        return parse_extraction(response.content)

    def persist(self, user_id: str, conversation_id: str, payload: ExtractionResult) -> ExtractionResult:
        logger.debug(
            "memory extraction categories user=%s conversation=%s goals=%d preferences=%d health=%d",
            user_id,
            conversation_id,
            len(payload.goals),
            len(payload.preferences),
            len(payload.health),
        )
        for goal in payload.goals:
            if not goal.description.strip():
                continue
            saved = self.store.add_goal(
                Goal(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    goal_description=goal.description.strip(),
                    status="active",
                )
            )
            self.store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_type="goal",
                    memory_content=saved.goal_description,
                    source="user_reported",
                    confidence=0.9,
                )
            )
        for preference in payload.preferences:
            if preference.content.strip():
                self.store.add_memory(
                    MemoryRecord(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        memory_type="preference",
                        memory_content=preference.content.strip(),
                        source="user_reported",
                        confidence=0.8,
                        memory_key=memory_key(preference.content),
                    )
                )
        for health in payload.health:
            if health.concern.strip():
                continue
        for obstacle in payload.obstacles:
            if not obstacle.description.strip():
                continue
            goal = self.store.latest_goal_for_hint(user_id, obstacle.goal_hint)
            self.store.add_obstacle(
                Obstacle(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    goal_id=goal.id if goal else None,
                    obstacle_description=obstacle.description.strip(),
                )
            )
            self.store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_type="obstacle",
                    memory_content=obstacle.description.strip(),
                    source="user_reported",
                    confidence=0.85,
                )
            )
            if goal and goal.status == "active":
                self.store.update_goal_status(user_id, goal.id, "needs_attention")
        for recommendation in payload.recommendations:
            if not recommendation.text.strip():
                continue
            goal = self.store.latest_goal_for_hint(user_id, recommendation.goal_hint)
            self.store.add_recommendation(
                Recommendation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    goal_id=goal.id if goal else None,
                    recommendation=recommendation.text.strip(),
                    status="proposed",
                )
            )
            self.store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_type="recommendation",
                    memory_content=recommendation.text.strip(),
                    source="ai_generated",
                    confidence=0.7,
                )
            )
        for commitment in payload.commitments:
            if not commitment.description.strip():
                continue
            latest = self.store.latest_recommendation(user_id)
            self.store.add_commitment(
                Commitment(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    recommendation_id=latest.id if latest else None,
                    commitment_description=commitment.description.strip(),
                )
            )
            self.store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_type="commitment",
                    memory_content=commitment.description.strip(),
                    source="user_reported",
                    confidence=0.8,
                )
            )
        for outcome in payload.outcomes:
            if not outcome.reported_outcome.strip():
                continue
            latest = self.store.latest_commitment(user_id)
            self.store.add_outcome(
                Outcome(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    commitment_id=latest.id if latest else None,
                    reported_outcome=outcome.reported_outcome.strip(),
                )
            )
            self.store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_type="outcome",
                    memory_content=outcome.reported_outcome.strip(),
                    source="user_reported",
                    confidence=0.9,
                )
            )
        if payload.session_summary.strip():
            self.store.add_session_summary(
                SessionSummary(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    summary=payload.session_summary.strip(),
                )
            )
        return payload


def parse_extraction(raw: str) -> ExtractionResult:
    text = raw.strip()
    match = JSON_RE.search(text)
    if not match:
        return ExtractionResult(session_summary=text[:280])
    try:
        data: dict[str, Any] = json.loads(match.group(0))
        return ExtractionResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return ExtractionResult()
