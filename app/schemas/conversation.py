from __future__ import annotations
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None


class MessageCreate(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    confidence_score: float | None = None
    citations: list[dict[str, Any]] | None = None
    sources_used: list[str] | None = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    confidence_score: float | None = None
    citations: list[dict[str, Any]] | None = None
    sources_used: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    total: int
