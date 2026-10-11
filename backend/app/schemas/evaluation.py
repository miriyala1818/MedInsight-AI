from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConfidenceBucket(BaseModel):
    label: str
    count: int
    min_score: float = 0.0
    max_score: float = 0.0


class SourceCoverageItem(BaseModel):
    source_name: str
    coverage_rate: float = Field(ge=0.0, le=1.0)
    evidence_count: int = 0
    hallucination_rate: float = Field(ge=0.0, le=1.0)


class EvaluationMetricSeriesPoint(BaseModel):
    timestamp: datetime
    value: float = Field(ge=0.0, le=1.0)


class EvaluationDashboardResponse(BaseModel):
    hallucination_rate: float = Field(ge=0.0, le=1.0)
    citation_accuracy: float = Field(ge=0.0, le=1.0)
    retrieval_precision: float = Field(ge=0.0, le=1.0)
    source_coverage: float = Field(ge=0.0, le=1.0)
    confidence_distribution: list[ConfidenceBucket] = Field(default_factory=list)
    confidence_level_counts: dict[str, int] = Field(default_factory=dict)
    source_coverage_breakdown: list[SourceCoverageItem] = Field(default_factory=list)
    confidence_trend: list[EvaluationMetricSeriesPoint] = Field(default_factory=list)
    citation_accuracy_trend: list[EvaluationMetricSeriesPoint] = Field(default_factory=list)
    retrieval_precision_trend: list[EvaluationMetricSeriesPoint] = Field(default_factory=list)
    generated_at: datetime
    total_runs: int = 0
    total_sessions: int = 0


class EvaluationRunInput(BaseModel):
    session_id: str | None = None
    query_id: str | None = None
    answer_id: str | None = None
    hallucination_detected: bool = False
    citation_accuracy: float = Field(ge=0.0, le=1.0)
    retrieval_precision: float = Field(ge=0.0, le=1.0)
    source_coverage: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=100.0)
    confidence_level: str
    contradictions_found: bool = False
    explanation: str = ""
