from __future__ import annotations
import uuid
from datetime import datetime, UTC
from typing import Optional, Any

from pydantic import BaseModel, Field

from app.db.base import MongoBase


class Message(MongoBase):
    """MongoDB model for conversation messages"""

    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    confidence_score: Optional[float] = None
    citations: Optional[list[dict[str, Any]]] = None
    sources_used: Optional[list[str]] = None


class Conversation(MongoBase):
    """MongoDB model for conversations"""

    title: str = "New Conversation"
    messages: list[Message] = Field(default_factory=list)
