from __future__ import annotations

from datetime import date
import json

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.deps import CurrentUser, get_current_user
from src.agent.coach import WellnessCoach
from src.data.health_service import HealthService
from src.database.models import MemoryRecord, UserProfile
from src.database.repository import SupabaseCareStore
from src.llm.exceptions import LLMError
from src.llm.groq_client import GroqClient
from src.services.conversation_service import ConversationService
from src.services.text_utils import (
    canonical_category,
    canonical_memory_key,
    extract_weight_update,
    is_near_duplicate,
    is_single_value_key,
    normalize_canonical_key,
)

router = APIRouter(prefix="/api", tags=["care"])


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=120)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    is_pinned: bool | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    memory_type: str = Field(default="preference", max_length=40)
    conversation_id: str | None = None
    importance: float = 0.7


class MemoryConfirmCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    memory_type: str = Field(default="health", max_length=40)
    conversation_id: str | None = None


class MemoryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    age: int | None = None
    date_of_birth: str | None = None
    sex: str | None = None
    height: float | None = None
    current_weight: float | None = None
    unit_preference: str | None = None
    primary_goal: str | None = None
    goals: list[str] | None = None
    activity_level: str | None = None
    dietary_preference: str | None = None
    allergies: str | None = None
    medical_conditions: str | None = None
    medications: str | None = None
    injuries_limitations: str | None = None
    sleep_duration_hours: float | None = None
    sleep_quality: str | None = None
    lifestyle_notes: str | None = None


class OnboardingPayload(BaseModel):
    full_name: str = Field(default="", max_length=100)
    age: int | None = Field(default=None, ge=1, le=120)
    date_of_birth: str | None = None
    sex: str = Field(default="prefer_not_to_say")
    height: float | None = Field(default=None, ge=30, le=300)
    current_weight: float | None = Field(default=None, ge=20, le=400)
    unit_preference: str = Field(default="metric")
    primary_goal: str = Field(default="")
    goals: list[str] = Field(default_factory=list)
    activity_level: str = Field(default="sedentary")
    dietary_preference: str = Field(default="any")
    allergies: str = Field(default="")
    medical_conditions: str = Field(default="")
    medications: str = Field(default="")
    injuries_limitations: str = Field(default="")
    sleep_duration_hours: float | None = Field(default=None, ge=0, le=24)
    sleep_quality: str = Field(default="")
    lifestyle_notes: str = Field(default="")


def _store(user: CurrentUser) -> SupabaseCareStore:
    return SupabaseCareStore(user.client)


def _conversation(value) -> dict:
    return value.model_dump(mode="json")


@router.get("/conversations")
def list_conversations(user: CurrentUser = Depends(get_current_user)):
    return [_conversation(item) for item in ConversationService(_store(user)).list(user.id)]


@router.post("/conversations")
def create_conversation(
    body: ConversationCreate,
    user: CurrentUser = Depends(get_current_user),
):
    item = ConversationService(_store(user)).create(user.id, body.title)
    return _conversation(item)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    store = _store(user)
    conversation = store.get_conversation(user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {
        "conversation": _conversation(conversation),
        "messages": [item.model_dump(mode="json") for item in store.list_messages(user.id, conversation_id)],
    }


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    service = ConversationService(_store(user))
    try:
        if body.title is not None:
            item = service.rename(user.id, conversation_id, body.title)
        elif body.is_pinned is not None:
            item = service.set_pinned(user.id, conversation_id, body.is_pinned)
        else:
            raise HTTPException(status_code=400, detail="No conversation change was provided.")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _conversation(item)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    try:
        ConversationService(_store(user)).delete(user.id, conversation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    body: MessageCreate,
    user: CurrentUser = Depends(get_current_user),
):
    store = _store(user)
    coach = WellnessCoach(
        store,
        GroqClient(),
        health_service=HealthService(),
    )
    try:
        turn = coach.respond(user.id, conversation_id, body.content)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "assistant_message": turn.assistant_message,
        "conversation_title": turn.conversation_title,
        "conversation_id": conversation_id,
        "memories_used": [item.__dict__ for item in turn.memories_used],
        "pending_memories": [
            {"category": "health", "content": item.concern, "conversation_id": conversation_id}
            for item in (turn.extraction.health if turn.extraction else [])
            if item.concern.strip()
        ],
        "health_used": turn.health_used.__dict__ if turn.health_used else None,
    }


@router.post("/conversations/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: str,
    body: MessageCreate,
    user: CurrentUser = Depends(get_current_user),
):
    store = _store(user)
    coach = WellnessCoach(
        store,
        GroqClient(),
        health_service=HealthService(),
    )

    def event_stream():
        try:
            for chunk in coach.stream_respond(user.id, conversation_id, body.content):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/memory")
def list_memory(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    include_history: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
):
    store = _store(user)
    items = []
    seen_single_keys: set[str] = set()
    search_lower = search.strip().lower() if search else ""

    for memory in store.list_memories(user.id):
        if memory.memory_type == "setting" or not memory.confirmed:
            continue
        if not include_history and not memory.is_current:
            continue

        # Canonical key and category resolution
        c_key = normalize_canonical_key(memory.memory_key, memory.memory_type, memory.memory_content)
        cat = canonical_category(c_key, memory.memory_content, memory.memory_type)

        # Single-value deduplication: only latest current value appears as current
        if not include_history and c_key and is_single_value_key(c_key):
            if c_key in seen_single_keys:
                continue
            seen_single_keys.add(c_key)

        if category and category.lower() != "all" and cat.lower() != category.lower():
            continue
        if search_lower and search_lower not in memory.memory_content.lower():
            continue

        items.append({
            "id": memory.id,
            "category": cat,
            "label": cat.replace("_", " ").title(),
            "text": memory.memory_content,
            "key": c_key,
            "importance": getattr(memory, "importance", 0.7),
            "confidence": getattr(memory, "confidence", 0.7),
            "confirmed": memory.confirmed,
            "is_current": memory.is_current,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
        })

    # Include legacy goals from goals table only if not already present from user_memories
    if not category or category.lower() in {"all", "goal"}:
        seen_goals = {it["text"].lower() for it in items if it["category"] == "goal"}
        for goal in store.list_goals(user.id):
            desc = goal.goal_description.strip()
            if any(is_near_duplicate(desc, existing) for existing in seen_goals):
                continue
            if search_lower and search_lower not in desc.lower():
                continue
            seen_goals.add(desc.lower())
            items.append({
                "id": f"goal:{goal.id}",
                "category": "goal",
                "label": "Goal",
                "text": f"{desc} (status: {goal.status})",
                "importance": 0.85,
                "confidence": 0.9,
                "confirmed": True,
                "is_current": goal.status != "completed",
                "created_at": goal.created_at.isoformat(),
                "updated_at": goal.updated_at.isoformat(),
            })

    return items[:50]


@router.post("/memory")
def create_memory(body: MemoryCreate, user: CurrentUser = Depends(get_current_user)):
    c_key = normalize_canonical_key(None, body.memory_type, body.content)
    cat = canonical_category(c_key, body.content, body.memory_type)
    content = body.content.strip()
    if c_key == "current_weight":
        weight_update = extract_weight_update(content)
        if weight_update:
            content = weight_update[2]

    memory = MemoryRecord(
        user_id=user.id,
        conversation_id=body.conversation_id,
        memory_type=cat,
        memory_content=content,
        source="user_reported",
        confidence=1.0,
        importance=body.importance,
        confirmed=True,
        is_current=True,
        memory_key=c_key,
    )
    return _store(user).add_memory(memory).model_dump(mode="json")


@router.patch("/memory/{memory_id}")
def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        content = body.content.strip()
        weight_update = extract_weight_update(content)
        if weight_update:
            content = weight_update[2]
        return _store(user).update_memory(user.id, memory_id, content).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/memory/{memory_id}")
def get_memory(memory_id: str, user: CurrentUser = Depends(get_current_user)):
    item = _store(user).get_memory(user.id, memory_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return item.model_dump(mode="json")


@router.delete("/memory/{memory_id}")
def delete_memory(memory_id: str, user: CurrentUser = Depends(get_current_user)):
    try:
        _store(user).delete_memory(user.id, memory_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/profile")
def get_user_profile(user: CurrentUser = Depends(get_current_user)):
    store = _store(user)
    profile = store.get_profile(user.id)
    return {
        "profile": profile.model_dump(mode="json") if profile else None,
        "onboarding_completed": bool(profile and profile.onboarding_completed),
    }


@router.get("/profile/{profile_id}")
def get_profile_by_id(profile_id: str, user: CurrentUser = Depends(get_current_user)):
    store = _store(user)
    profile = store.get_profile(user.id)
    if profile is None or (profile.id != profile_id and user.id != profile_id):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return {
        "profile": profile.model_dump(mode="json"),
        "onboarding_completed": profile.onboarding_completed,
    }


@router.post("/profile/onboarding")
def complete_onboarding(body: OnboardingPayload, user: CurrentUser = Depends(get_current_user)):
    store = _store(user)
    profile = UserProfile(
        user_id=user.id,
        full_name=body.full_name.strip(),
        age=body.age,
        date_of_birth=body.date_of_birth,
        sex=body.sex,
        height=body.height,
        current_weight=body.current_weight,
        unit_preference=body.unit_preference,
        primary_goal=body.primary_goal,
        goals=body.goals,
        activity_level=body.activity_level,
        dietary_preference=body.dietary_preference,
        allergies=body.allergies.strip(),
        medical_conditions=body.medical_conditions.strip(),
        medications=body.medications.strip(),
        injuries_limitations=body.injuries_limitations.strip(),
        sleep_duration_hours=body.sleep_duration_hours,
        sleep_quality=body.sleep_quality,
        lifestyle_notes=body.lifestyle_notes.strip(),
        onboarding_completed=True,
    )
    saved = store.save_profile(profile)

    # Establish baseline memories for the user
    if profile.full_name:
        store.add_memory(MemoryRecord(
            user_id=user.id,
            memory_type="profile",
            memory_content=f"User's name is {profile.full_name}.",
            memory_key="name",
            confirmed=True,
            is_current=True,
        ))
    if profile.current_weight:
        unit = "kg" if profile.unit_preference == "metric" else "lbs"
        store.add_memory(MemoryRecord(
            user_id=user.id,
            memory_type="health",
            memory_content=f"User's weight is {profile.current_weight} {unit}.",
            memory_key="current_weight",
            confirmed=True,
            is_current=True,
        ))
    if profile.height:
        unit = "cm" if profile.unit_preference == "metric" else "inches"
        store.add_memory(MemoryRecord(
            user_id=user.id,
            memory_type="health",
            memory_content=f"User's height is {profile.height} {unit}.",
            memory_key="height",
            confirmed=True,
            is_current=True,
        ))
    if profile.dietary_preference and profile.dietary_preference != "any":
        store.add_memory(MemoryRecord(
            user_id=user.id,
            memory_type="health",
            memory_content=f"User follows a {profile.dietary_preference} diet.",
            memory_key="dietary_preference",
            confirmed=True,
            is_current=True,
        ))
    if profile.primary_goal or profile.goals:
        goal_text = profile.primary_goal or ", ".join(profile.goals)
        store.add_memory(MemoryRecord(
            user_id=user.id,
            memory_type="goal",
            memory_content=f"Primary wellness goals: {goal_text}.",
            memory_key="primary_fitness_goal",
            confirmed=True,
            is_current=True,
        ))

    return {"ok": True, "profile": saved.model_dump(mode="json")}


@router.put("/profile")
def update_user_profile(body: ProfileUpdate, user: CurrentUser = Depends(get_current_user)):
    store = _store(user)
    existing = store.get_profile(user.id)
    if existing is None:
        existing = UserProfile(user_id=user.id)
        store.save_profile(existing)

    updates = body.model_dump(exclude_unset=True)
    updated = store.update_profile(user.id, updates)

    # Sync weight update if weight was changed
    if body.current_weight is not None:
        unit = "kg" if updated.unit_preference == "metric" else "lbs"
        store.add_memory(MemoryRecord(
            user_id=user.id,
            memory_type="health",
            memory_content=f"User's weight is {body.current_weight} {unit}.",
            memory_key="current_weight",
            confirmed=True,
            is_current=True,
        ))
    if body.height is not None:
        unit = "cm" if updated.unit_preference == "metric" else "inches"
        store.add_memory(MemoryRecord(
            user_id=user.id,
            memory_type="health",
            memory_content=f"User's height is {body.height} {unit}.",
            memory_key="height",
            confirmed=True,
            is_current=True,
        ))

    return {"ok": True, "profile": updated.model_dump(mode="json")}


@router.delete("/memory")
def clear_memory(user: CurrentUser = Depends(get_current_user)):
    _store(user).clear_memories(user.id)
    return {"ok": True}


@router.post("/memory/confirm")
def confirm_memory(body: MemoryConfirmCreate, user: CurrentUser = Depends(get_current_user)):
    content = body.content.strip()
    c_key = normalize_canonical_key(None, body.memory_type, content)
    cat = canonical_category(c_key, content, body.memory_type)
    if c_key == "current_weight":
        weight_update = extract_weight_update(content)
        if weight_update:
            content = weight_update[2]

    memory = MemoryRecord(
        user_id=user.id,
        memory_type=cat,
        memory_content=content,
        conversation_id=body.conversation_id,
        source="user_reported",
        confidence=1.0,
        importance=0.95,
        confirmed=True,
        is_current=True,
        memory_key=c_key,
    )
    return _store(user).add_memory(memory).model_dump(mode="json")


@router.get("/dashboard")
def dashboard(
    participant: str | None = None,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
):
    health = HealthService()
    participants = health.available_participants()
    if not participants:
        return {"participants": [], "participant": None, "metrics": [], "points": []}
    selected = participant if participant in participants else participants[0]
    frame = health.participant_frame(selected)
    frame = health.filter_dates(frame, start, end)
    labels = {
        "steps": "Daily steps",
        "sleep_hours": "Sleep hours",
        "active_minutes": "Active minutes",
        "resting_heart_rate": "Resting heart rate",
    }
    available = [
        (key, label)
        for key, label in labels.items()
        if key in frame.columns and frame[key].notna().any()
    ]
    metrics = []
    for key, label in available:
        summary = health.metric_card(frame, key)
        metrics.append({"key": key, "label": label, **summary})
    chart_key, chart_label = available[0] if available else (None, None)
    points = []
    if chart_key:
        for row in frame[["measurement_date", chart_key]].dropna().to_dict("records"):
            points.append({
                "date": pd.Timestamp(row["measurement_date"]).date().isoformat(),
                "value": float(row[chart_key]),
            })
    return {
        "participants": participants,
        "participant": selected,
        "date_start": str(frame["measurement_date"].min().date()) if not frame.empty else None,
        "date_end": str(frame["measurement_date"].max().date()) if not frame.empty else None,
        "metrics": metrics,
        "chart": {"label": chart_label, "points": points},
        "source": "PMData research demo data",
    }
