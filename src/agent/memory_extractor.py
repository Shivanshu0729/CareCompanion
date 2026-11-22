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
from src.llm.prompts import MEMORY_EXTRACTION_PROMPT, is_meal_plan_request
from src.llm.provider import LLMMessage, LLMProvider
from src.services.single_user_guard import contains_third_party_reference
from src.services.text_utils import (
    canonical_category,
    canonical_memory_key,
    extract_weight_update,
    is_credential_or_secret,
    normalize_canonical_key,
    tokenize,
)

logger = logging.getLogger(__name__)

# Broad conversational markers to avoid dropping relevant memory
CONVERSATIONAL_MARKERS = {
    "i", "my", "im", "i'm", "we", "we're", "our", "me", "am", "have", "had", "prefer", "want", "like", "need",
    "learning", "learn", "studying", "study", "python", "java", "project", "building", "built", "develop",
    "architecture", "stack", "goal", "career", "job", "internship", "work", "engineer", "working", "routine",
    "health", "condition", "lung", "lungs", "breathing", "breath", "asthma", "heart", "pain", "injury", "sleep",
    "weight", "weigh", "height", "age", "years", "name", "allergic", "allergy", "diet", "food", "vegetarian",
    "vegan", "keto", "meat", "milestone", "completed", "finished", "started", "status", "decided", "decision",
    "doctor", "medication", "medicine", "treatment", "exercise", "workout", "run", "running", "walk"
}


class ExtractedMemory(BaseModel):
    category: str  # profile, goal, context, progress, preference, health
    key: str | None = None
    value: str
    action: str = "new"  # new, update, repeat, temporary
    importance: float = 0.7
    confidence: float = 0.8
    requires_consent: bool = False


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
    memories: list[ExtractedMemory] = Field(default_factory=list)
    # Legacy fields for backward compatibility with existing tests and services
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
        if is_credential_or_secret(user_message):
            # Do not extract credentials or secret payloads
            return False

        if is_meal_plan_request(user_message) and not any(k in user_message.lower() for k in ("allergic", "allergy", "vegan", "vegetarian", "my weight", "weigh", "health", "goal")):
            return False

        combined = f"{user_message} {assistant_message}".lower()
        tokens = tokenize(combined)
        return bool(tokens & CONVERSATIONAL_MARKERS) or "bedtime" in combined

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
        return parse_extraction(response.content, user_message=user_message)

    def persist(self, user_id: str, conversation_id: str, payload: ExtractionResult) -> ExtractionResult:
        # Strictly single-user: Filter out any items referring to third parties
        payload.memories = [m for m in payload.memories if not contains_third_party_reference(m.value)]
        payload.goals = [g for g in payload.goals if not contains_third_party_reference(g.description)]
        payload.preferences = [p for p in payload.preferences if not contains_third_party_reference(p.content)]
        payload.health = [h for h in payload.health if not contains_third_party_reference(h.concern)]
        payload.obstacles = [o for o in payload.obstacles if not contains_third_party_reference(o.description)]

        logger.debug(
            "memory extraction categories user=%s conversation=%s general=%d goals=%d preferences=%d health=%d",
            user_id,
            conversation_id,
            len(payload.memories),
            len(payload.goals),
            len(payload.preferences),
            len(payload.health),
        )

        # 1. Persist General Categorized Memories
        for mem in payload.memories:
            if mem.action == "temporary" or mem.confidence < 0.4:
                continue
            if is_credential_or_secret(mem.value):
                continue
            if not mem.value.strip():
                continue

            c_key = normalize_canonical_key(mem.key, mem.category, mem.value)
            cat = canonical_category(c_key, mem.value, mem.category)
            if c_key in {"current_weight", "weight", "height", "current_height", "age", "name"}:
                mem.requires_consent = False

            # Sensitive health memories requiring user confirmation flow (severe disease, chronic illness)
            if cat == "health" and mem.requires_consent:
                # Keep in payload.health so the frontend modal can ask user for consent
                if not any(h.concern == mem.value for h in payload.health):
                    payload.health.append(ExtractedHealth(concern=mem.value))
                continue

            record = MemoryRecord(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type=cat,
                memory_content=mem.value.strip(),
                source="user_reported",
                confidence=mem.confidence,
                importance=mem.importance,
                confirmed=True,
                is_current=True,
                memory_key=c_key,
            )
            self.store.add_memory(record)

            # If it's a goal, mirror into goals table for goals view
            if mem.category == "goal":
                self.store.add_goal(
                    Goal(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        goal_description=mem.value.strip(),
                        status="active",
                    )
                )

        # 2. Persist Legacy Goals (for test and legacy compatibility)
        for goal in payload.goals:
            if not goal.description.strip() or is_credential_or_secret(goal.description):
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
                    importance=0.85,
                    memory_key=canonical_memory_key("goal", saved.goal_description),
                )
            )

        # 3. Persist Legacy Preferences
        for preference in payload.preferences:
            if not preference.content.strip() or is_credential_or_secret(preference.content):
                continue
            c_key = normalize_canonical_key(None, "preference", preference.content)
            self.store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_type="preference",
                    memory_content=preference.content.strip(),
                    source="user_reported",
                    confidence=0.85,
                    importance=0.75,
                    memory_key=c_key,
                )
            )

        # 4. Legacy Health records that require explicit confirmation are held in payload.health
        # (They will be confirmed via the /api/memory/confirm endpoint)

        # 5. Persist Obstacles
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
                    importance=0.7,
                    memory_key=canonical_memory_key("obstacle", obstacle.description),
                )
            )
            if goal and goal.status == "active":
                self.store.update_goal_status(user_id, goal.id, "needs_attention")

        # 6. Persist Recommendations (Stored in recommendations table, not user_memories)
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

        # 7. Persist Commitments
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
                    importance=0.7,
                )
            )

        # 8. Persist Outcomes
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
                    importance=0.75,
                )
            )

        # 9. Persist Session Summary
        if payload.session_summary.strip():
            self.store.add_session_summary(
                SessionSummary(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    summary=payload.session_summary.strip(),
                )
            )

        return payload


def extract_explicit_facts(user_message: str) -> list[ExtractedMemory]:
    facts: list[ExtractedMemory] = []
    if not user_message:
        return facts

    # Explicit validated weight update (e.g. "my weight is 75 kg", "I weigh 80 kg", "my weight is now 75")
    weight_update = extract_weight_update(user_message)
    if weight_update:
        _, _, formatted = weight_update
        facts.append(
            ExtractedMemory(
                category="health",
                key="current_weight",
                value=formatted,
                action="update",
                importance=0.95,
                confidence=1.0,
                requires_consent=False,
            )
        )

    # Explicit name pattern (e.g. "my name is Shivanshu", "call me Shivanshu")
    name_match = re.search(
        r"\b(?:my\s+name\s+is|call\s+me)\s+([a-zA-Z]+)\b",
        user_message,
        re.IGNORECASE,
    )
    if name_match:
        name_val = name_match.group(1).strip()
        if name_val.lower() not in {"a", "the", "an", "now", "here"}:
            facts.append(
                ExtractedMemory(
                    category="profile",
                    key="name",
                    value=f"Name is {name_val.capitalize()}",
                    action="update",
                    importance=0.9,
                    confidence=1.0,
                )
            )

    # Explicit height pattern
    height_match = re.search(
        r"\b(?:my\s+height\s+is|height\s*[:=]?)\s*(\d+(?:\.\d+)?\s*(?:cm|ft|inches|meters|m)?)\b",
        user_message,
        re.IGNORECASE,
    )
    if height_match:
        h_val = height_match.group(1).strip()
        facts.append(
            ExtractedMemory(
                category="profile",
                key="height",
                value=f"Current height is {h_val}",
                action="update",
                importance=0.85,
                confidence=1.0,
            )
        )

    # Explicit age pattern
    age_match = re.search(
        r"\b(?:my\s+age\s+is|i\s+am)\s+(\d+)\s*(?:years\s+old)?\b",
        user_message,
        re.IGNORECASE,
    )
    if age_match:
        age_val = age_match.group(1).strip()
        facts.append(
            ExtractedMemory(
                category="profile",
                key="age",
                value=f"Age is {age_val} years old",
                action="update",
                importance=0.85,
                confidence=1.0,
            )
        )

    return facts


def parse_extraction(raw: str, user_message: str = "") -> ExtractionResult:
    text = raw.strip()
    explicit_facts = extract_explicit_facts(user_message)
    match = JSON_RE.search(text)
    if not match:
        return ExtractionResult(memories=explicit_facts, session_summary=text[:280])

    try:
        data: dict[str, Any] = json.loads(match.group(0))

        # Check for top-level memories array
        memories: list[ExtractedMemory] = []
        if "memories" in data and isinstance(data["memories"], list):
            for item in data["memories"]:
                try:
                    memories.append(ExtractedMemory.model_validate(item))
                except ValidationError:
                    continue

        # Merge explicit facts to guarantee single-value facts are never missed
        for fact in explicit_facts:
            existing_idx = next((i for i, m in enumerate(memories) if m.key == fact.key), None)
            if existing_idx is not None:
                memories[existing_idx] = fact
            else:
                memories.append(fact)

        # Check legacy fields
        legacy = data.get("legacy", {})
        goals_data = data.get("goals") or legacy.get("goals") or []
        prefs_data = data.get("preferences") or legacy.get("preferences") or []
        obstacles_data = data.get("obstacles") or legacy.get("obstacles") or []
        recs_data = data.get("recommendations") or legacy.get("recommendations") or []
        commitments_data = data.get("commitments") or legacy.get("commitments") or []
        outcomes_data = data.get("outcomes") or legacy.get("outcomes") or []
        health_data = data.get("health") or legacy.get("health") or []
        summary = str(data.get("session_summary") or legacy.get("session_summary") or "")

        filtered_health: list[ExtractedHealth] = []
        for h in health_data:
            if isinstance(h, dict):
                eh = ExtractedHealth.model_validate(h)
                c_key = normalize_canonical_key(None, "health", eh.concern)
                if c_key in {"current_weight", "weight"}:
                    weight_update = extract_weight_update(eh.concern)
                    val = weight_update[2] if weight_update else eh.concern
                    if not any(m.key in {"current_weight", "weight"} for m in memories):
                        memories.append(
                            ExtractedMemory(
                                category="health",
                                key="current_weight",
                                value=val,
                                action="update",
                                importance=0.95,
                                confidence=1.0,
                                requires_consent=False,
                            )
                        )
                elif c_key in {"height", "age", "name"}:
                    if not any(m.key == c_key for m in memories):
                        memories.append(
                            ExtractedMemory(
                                category=canonical_category(c_key, eh.concern),
                                key=c_key,
                                value=eh.concern,
                                action="update",
                                importance=0.85,
                                confidence=0.9,
                                requires_consent=False,
                            )
                        )
                else:
                    filtered_health.append(eh)

        result = ExtractionResult(
            memories=memories,
            goals=[ExtractedGoal.model_validate(g) for g in goals_data if isinstance(g, dict)],
            preferences=[ExtractedPreference.model_validate(p) for p in prefs_data if isinstance(p, dict)],
            obstacles=[ExtractedObstacle.model_validate(o) for o in obstacles_data if isinstance(o, dict)],
            recommendations=[ExtractedRecommendation.model_validate(r) for r in recs_data if isinstance(r, dict)],
            commitments=[ExtractedCommitment.model_validate(c) for c in commitments_data if isinstance(c, dict)],
            outcomes=[ExtractedOutcome.model_validate(out) for out in outcomes_data if isinstance(out, dict)],
            health=filtered_health,
            session_summary=summary,
        )
        return result
    except (json.JSONDecodeError, ValidationError):
        return ExtractionResult(memories=explicit_facts)
