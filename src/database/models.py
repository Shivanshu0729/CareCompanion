from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

MemoryType = Literal[
    "goal",
    "preference",
    "obstacle",
    "recommendation",
    "commitment",
    "outcome",
    "health",
    "setting",
]
GoalStatus = Literal["active", "needs_attention", "completed", "paused"]
ItemStatus = Literal["proposed", "accepted", "adjusted", "completed", "abandoned"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Conversation(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    title: str = "New conversation"
    is_pinned: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Message(BaseModel):
    id: str = Field(default_factory=new_id)
    conversation_id: str
    user_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=utcnow)


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    conversation_id: str | None = None
    memory_type: MemoryType
    memory_content: str
    source: str = "user_reported"
    confidence: float = 0.7
    confirmed: bool = True
    is_current: bool = True
    memory_key: str | None = None
    superseded_by: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SessionSummary(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    conversation_id: str
    summary: str
    created_at: datetime = Field(default_factory=utcnow)


class Goal(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    conversation_id: str | None = None
    goal_description: str
    status: GoalStatus = "active"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Recommendation(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    conversation_id: str | None = None
    goal_id: str | None = None
    recommendation: str
    status: ItemStatus = "proposed"
    created_at: datetime = Field(default_factory=utcnow)


class Commitment(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    conversation_id: str | None = None
    recommendation_id: str | None = None
    commitment_description: str
    status: ItemStatus = "accepted"
    created_at: datetime = Field(default_factory=utcnow)


class Outcome(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    conversation_id: str | None = None
    commitment_id: str | None = None
    reported_outcome: str
    created_at: datetime = Field(default_factory=utcnow)


class Obstacle(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    conversation_id: str | None = None
    goal_id: str | None = None
    obstacle_description: str
    created_at: datetime = Field(default_factory=utcnow)


class HealthSummary(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    participant_id: str
    metric_type: str
    metric_value: float | None = None
    measurement_date: str
    source: str = "pmdata"
    created_at: datetime = Field(default_factory=utcnow)


def row_to_model(model_cls: type[BaseModel], row: dict[str, Any]) -> BaseModel:
    return model_cls.model_validate(row)
