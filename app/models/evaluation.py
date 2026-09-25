from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.base import MongoBase


class EvaluationRun(MongoBase):
    """MongoDB model for evaluation runs"""

    session_id: Optional[str] = None
    query_id: Optional[str] = None
    answer_id: Optional[str] = None
    hallucination_detected: bool = False
    citation_accuracy: float = 0.0
    retrieval_precision: float = 0.0
    source_coverage: float = 0.0
    confidence_score: float = 0.0
    confidence_level: str = "Low"
    contradictions_found: bool = False
    explanation: str = ""


class EvaluationMetricSnapshot(MongoBase):
    """MongoDB model for evaluation metric snapshots"""

    run_id: str
    metric_name: str
    metric_value: float = 0.0
    bucket_label: str = ""
    source_name: str = ""


class EvaluationAuditEvent(MongoBase):
    """MongoDB model for evaluation audit events"""

    run_id: Optional[str] = None
    event_type: str
    payload_json: str = "{}"
