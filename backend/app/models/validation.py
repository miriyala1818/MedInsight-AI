from __future__ import annotations

from pydantic import BaseModel, Field


class ValidationOutput(BaseModel):
    confidence_score: int = Field(ge=0, le=100)
    confidence_level: str
    contradictions_found: bool
    explanation: str
    is_supported: bool = False
    sources_count: int = 0
    agreement_score: float = 0.0
    credibility_score: float = 0.0
    recency_score: float = 0.0
