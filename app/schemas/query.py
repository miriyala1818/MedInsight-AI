from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    conversation_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    confidence_score: float
    citations: list[dict[str, Any]]
    request_id: str | None = None
    trace_id: str | None = None
    conversation_id: str | None = None
    sources_used: list[str] = Field(default_factory=list)
