from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import CurrentUser, get_current_user
from src.agent.coach import WellnessCoach
from src.data.health_service import HealthService
from src.database.models import MemoryRecord
from src.database.repository import SupabaseCareStore
from src.llm.groq_client import GroqClient
from src.services.conversation_service import ConversationService

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


class MemoryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


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
    return {
        "assistant_message": turn.assistant_message,
        "memories_used": [item.__dict__ for item in turn.memories_used],
        "pending_memories": [
            {"category": "health", "content": item.concern, "conversation_id": conversation_id}
            for item in (turn.extraction.health if turn.extraction else [])
            if item.concern.strip()
        ],
        "health_used": turn.health_used.__dict__ if turn.health_used else None,
    }


@router.get("/memory")
def list_memory(user: CurrentUser = Depends(get_current_user)):
    store = _store(user)
    items = []
    for memory in store.list_memories(user.id):
        if memory.memory_type == "setting" or not memory.confirmed or not memory.is_current:
            continue
        items.append({
            "id": memory.id,
            "label": memory.memory_type.replace("_", " ").title(),
            "text": memory.memory_content,
            "confirmed": memory.confirmed,
            "is_current": memory.is_current,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
        })
    for goal in store.list_goals(user.id)[:3]:
        items.append({"id": f"goal:{goal.id}", "label": "Goal", "text": goal.goal_description})
    for summary in store.list_session_summaries(user.id)[:1]:
        items.append({"id": f"summary:{summary.id}", "label": "Last session", "text": summary.summary})
    return items[:12]


@router.post("/memory")
def create_memory(body: MemoryCreate, user: CurrentUser = Depends(get_current_user)):
    memory = MemoryRecord(
        user_id=user.id,
        memory_type=body.memory_type,
        memory_content=body.content.strip(),
        source="user_reported",
        confidence=1.0,
        confirmed=True,
    )
    return _store(user).add_memory(memory).model_dump(mode="json")


@router.patch("/memory/{memory_id}")
def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        return _store(user).update_memory(user.id, memory_id, body.content.strip()).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/memory/{memory_id}")
def delete_memory(memory_id: str, user: CurrentUser = Depends(get_current_user)):
    _store(user).delete_memory(user.id, memory_id)
    return {"ok": True}


@router.delete("/memory")
def clear_memory(user: CurrentUser = Depends(get_current_user)):
    _store(user).clear_memories(user.id)
    return {"ok": True}


@router.post("/memory/confirm")
def confirm_memory(body: MemoryCreate, user: CurrentUser = Depends(get_current_user)):
    if body.memory_type != "health":
        raise HTTPException(status_code=400, detail="Only health memories require confirmation.")
    memory = MemoryRecord(
        user_id=user.id,
        memory_type="health",
        memory_content=f"User-reported health concern: {body.content.strip()}",
        conversation_id=body.conversation_id,
        source="user_reported",
        confidence=0.85,
        confirmed=True,
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
