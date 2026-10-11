from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import Settings, get_settings
from app.models.evaluation import EvaluationRun
from app.schemas.evaluation import (
    ConfidenceBucket,
    EvaluationDashboardResponse,
    EvaluationMetricSeriesPoint,
    EvaluationRunInput,
    SourceCoverageItem,
)


@dataclass(slots=True)
class EvaluationSummary:
    hallucination_rate: float
    citation_accuracy: float
    retrieval_precision: float
    source_coverage: float
    confidence_distribution: list[ConfidenceBucket]
    confidence_level_counts: dict[str, int]
    source_coverage_breakdown: list[SourceCoverageItem]
    confidence_trend: list[EvaluationMetricSeriesPoint]
    citation_accuracy_trend: list[EvaluationMetricSeriesPoint]
    retrieval_precision_trend: list[EvaluationMetricSeriesPoint]
    generated_at: datetime
    total_runs: int
    total_sessions: int


class EvaluationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def calculate_dashboard(self, runs: list[EvaluationRun | dict[str, Any]]) -> EvaluationDashboardResponse:
        normalized_runs = [self._normalize_run(run) for run in runs]
        summary = self._summarize(normalized_runs)
        return EvaluationDashboardResponse.model_validate(asdict(summary))

    def calculate_from_input(self, payload: EvaluationRunInput) -> dict[str, Any]:
        run = EvaluationRunInput.model_validate(payload)
        hallucination_rate = 1.0 if run.hallucination_detected or run.contradictions_found else 0.0
        return {
            "hallucination_rate": hallucination_rate,
            "citation_accuracy": run.citation_accuracy,
            "retrieval_precision": run.retrieval_precision,
            "source_coverage": run.source_coverage,
            "confidence_score": run.confidence_score,
            "confidence_level": run.confidence_level,
        }

    def empty_dashboard(self) -> EvaluationDashboardResponse:
        now = datetime.now(UTC)
        return EvaluationDashboardResponse(
            hallucination_rate=0.0,
            citation_accuracy=0.0,
            retrieval_precision=0.0,
            source_coverage=0.0,
            confidence_distribution=self._default_confidence_buckets(),
            confidence_level_counts={"High": 0, "Medium": 0, "Low": 0},
            source_coverage_breakdown=[],
            confidence_trend=[],
            citation_accuracy_trend=[],
            retrieval_precision_trend=[],
            generated_at=now,
            total_runs=0,
            total_sessions=0,
        )

    def _summarize(self, runs: list[EvaluationRunInput]) -> EvaluationSummary:
        if not runs:
            empty = self.empty_dashboard()
            return EvaluationSummary(
                hallucination_rate=empty.hallucination_rate,
                citation_accuracy=empty.citation_accuracy,
                retrieval_precision=empty.retrieval_precision,
                source_coverage=empty.source_coverage,
                confidence_distribution=empty.confidence_distribution,
                confidence_level_counts=empty.confidence_level_counts,
                source_coverage_breakdown=empty.source_coverage_breakdown,
                confidence_trend=empty.confidence_trend,
                citation_accuracy_trend=empty.citation_accuracy_trend,
                retrieval_precision_trend=empty.retrieval_precision_trend,
                generated_at=empty.generated_at,
                total_runs=empty.total_runs,
                total_sessions=empty.total_sessions,
            )

        total_runs = len(runs)
        total_sessions = len({run.session_id for run in runs if run.session_id})
        hallucination_rate = self._mean(1.0 if run.hallucination_detected or run.contradictions_found else 0.0 for run in runs)
        citation_accuracy = self._mean(run.citation_accuracy for run in runs)
        retrieval_precision = self._mean(run.retrieval_precision for run in runs)
        source_coverage = self._mean(run.source_coverage for run in runs)

        confidence_distribution = self._confidence_distribution(runs)
        confidence_level_counts = Counter(run.confidence_level for run in runs)
        source_coverage_breakdown = self._source_coverage_breakdown(runs)
        generated_at = datetime.now(UTC)

        trend_window = self._trend_window(runs)
        confidence_trend = self._series_from_window(trend_window, lambda run: run.confidence_score / 100.0)
        citation_accuracy_trend = self._series_from_window(trend_window, lambda run: run.citation_accuracy)
        retrieval_precision_trend = self._series_from_window(trend_window, lambda run: run.retrieval_precision)

        return EvaluationSummary(
            hallucination_rate=round(hallucination_rate, 4),
            citation_accuracy=round(citation_accuracy, 4),
            retrieval_precision=round(retrieval_precision, 4),
            source_coverage=round(source_coverage, 4),
            confidence_distribution=confidence_distribution,
            confidence_level_counts=dict(confidence_level_counts),
            source_coverage_breakdown=source_coverage_breakdown,
            confidence_trend=confidence_trend,
            citation_accuracy_trend=citation_accuracy_trend,
            retrieval_precision_trend=retrieval_precision_trend,
            generated_at=generated_at,
            total_runs=total_runs,
            total_sessions=total_sessions,
        )

    def _normalize_run(self, run: EvaluationRun | dict[str, Any]) -> EvaluationRunInput:
        if isinstance(run, EvaluationRunInput):
            return run
        if isinstance(run, EvaluationRun):
            payload = {
                "session_id": run.session_id,
                "query_id": run.query_id,
                "answer_id": run.answer_id,
                "hallucination_detected": run.hallucination_detected,
                "citation_accuracy": run.citation_accuracy,
                "retrieval_precision": run.retrieval_precision,
                "source_coverage": run.source_coverage,
                "confidence_score": run.confidence_score,
                "confidence_level": run.confidence_level,
                "contradictions_found": run.contradictions_found,
                "explanation": run.explanation,
            }
            return EvaluationRunInput.model_validate(payload)
        return EvaluationRunInput.model_validate(run)

    def _confidence_distribution(self, runs: list[EvaluationRunInput]) -> list[ConfidenceBucket]:
        buckets = [
            ConfidenceBucket(label="Low", count=0, min_score=0, max_score=49),
            ConfidenceBucket(label="Medium", count=0, min_score=50, max_score=79),
            ConfidenceBucket(label="High", count=0, min_score=80, max_score=100),
        ]
        for run in runs:
            if run.confidence_score < 50:
                buckets[0].count += 1
            elif run.confidence_score < 80:
                buckets[1].count += 1
            else:
                buckets[2].count += 1
        return buckets

    def _default_confidence_buckets(self) -> list[ConfidenceBucket]:
        return [
            ConfidenceBucket(label="Low", count=0, min_score=0, max_score=49),
            ConfidenceBucket(label="Medium", count=0, min_score=50, max_score=79),
            ConfidenceBucket(label="High", count=0, min_score=80, max_score=100),
        ]

    def _source_coverage_breakdown(self, runs: list[EvaluationRunInput]) -> list[SourceCoverageItem]:
        source_names = ["PubMed", "Nature", "WHO", "NIH"]
        breakdown: list[SourceCoverageItem] = []
        total_runs = max(len(runs), 1)
        total_coverage = self._mean(run.source_coverage for run in runs) if runs else 0.0
        total_hallucination = self._mean(
            1.0 if run.hallucination_detected or run.contradictions_found else 0.0 for run in runs
        )
        for source in source_names:
            evidence_count = floor(total_runs / len(source_names)) if total_runs else 0
            coverage_rate = min(1.0, total_coverage)
            hallucination_rate = min(1.0, total_hallucination * (1.0 - coverage_rate))
            breakdown.append(
                SourceCoverageItem(
                    source_name=source,
                    coverage_rate=round(coverage_rate, 4),
                    evidence_count=evidence_count,
                    hallucination_rate=round(hallucination_rate, 4),
                )
            )
        return breakdown

    def _trend_window(self, runs: list[EvaluationRunInput]) -> list[EvaluationRunInput]:
        return runs[-12:]

    def _series_from_window(self, runs: list[EvaluationRunInput], selector) -> list[EvaluationMetricSeriesPoint]:
        if not runs:
            return []
        start = datetime.now(UTC) - timedelta(hours=len(runs))
        series: list[EvaluationMetricSeriesPoint] = []
        for index, run in enumerate(runs):
            series.append(
                EvaluationMetricSeriesPoint(
                    timestamp=start + timedelta(hours=index),
                    value=round(max(min(selector(run), 1.0), 0.0), 4),
                )
            )
        return series

    def _mean(self, values) -> float:
        values = list(values)
        if not values:
            return 0.0
        return sum(values) / len(values)

    async def save_evaluation_run(self, client: AsyncIOMotorClient, run_data: dict[str, Any]) -> str:
        """Save evaluation run to MongoDB"""
        db = client["medical_research"]
        result = await db["evaluation_runs"].insert_one(run_data)
        return str(result.inserted_id)

    async def get_evaluation_runs(self, client: AsyncIOMotorClient, session_id: str | None = None) -> list[dict]:
        """Get evaluation runs, optionally filtered by session"""
        db = client["medical_research"]
        query = {"session_id": session_id} if session_id else {}
        runs = await db["evaluation_runs"].find(query).to_list(None)
        return runs


__all__ = ["EvaluationService", "EvaluationSummary"]
