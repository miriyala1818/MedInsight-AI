from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GroundingCitation(BaseModel):
    source_name: str
    source_id: str
    title: str = ""
    url: str = ""
    snippet: str = ""
    section: str = ""


class GroundedStatement(BaseModel):
    text: str
    citations: list[GroundingCitation] = Field(default_factory=list)
    supported: bool = False
    reason: str = ""


class GroundedResponse(BaseModel):
    answer: str
    confidence_score: int
    confidence_level: str
    contradictions_found: bool = False
    explanation: str = ""
    source_map: list[GroundedStatement] = Field(default_factory=list)
    abstained: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
