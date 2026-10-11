from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    source_name: str
    source_type: str = "medical_research"
    adapter_name: str
    query: str
    page: int = 1
    page_size: int = 10
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    total_results: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)


class RetrievedDocument(BaseModel):
    source_name: str
    source_id: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    journal: str = ""
    publication_date: str = ""
    abstract: str = ""
    url: str = ""
    score: float = 0.0
    metadata: SourceMetadata


class SourceRetrievalResponse(BaseModel):
    query: str
    page: int = 1
    page_size: int = 10
    total_results: int = 0
    results: list[RetrievedDocument] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)
