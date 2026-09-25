from typing import Any, Literal

from typing_extensions import TypedDict


class SourceCitation(TypedDict, total=False):
    source_name: str
    source_id: str
    title: str
    url: str
    snippet: str
    section: str


class ResearchState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    question: str
    session_id: str
    conversation_history: list[dict[str, str]]  # Previous messages for context

    # ── Tracing ────────────────────────────────────────────────────────────
    trace_id: str
    request_id: str

    # ── Workflow control ───────────────────────────────────────────────────
    status: Literal[
        "planning",
        "retrieving",
        "generating",
        "validating",
        "citing",
        "answering",
        "completed",
        "error",
    ]
    next_step: Literal["retrieval", "generation", "validation", "citation", "response"]
    retry_counts: dict[str, int]

    # ── Planner outputs ────────────────────────────────────────────────────
    entities: list[str]           # extracted medical terms
    information_needs: list[str]  # rephrased search axes

    # ── Retrieval output ───────────────────────────────────────────────────
    retrieved_documents: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    sources_used: list[str]

    # ── Generation output ──────────────────────────────────────────────────
    draft_answer: str             # raw LLM response
    answer: str                   # final answer surfaced to the user
    confidence_score: float
    confidence_level: str

    # ── Validation output ──────────────────────────────────────────────────
    validation_summary: dict[str, Any]
    contradictions_found: bool
    is_supported: bool
    explanation: str
    evidence_score: float
    contradictions: list[str]
    abstain_reason: str

    # ── Citations ──────────────────────────────────────────────────────────
    citations: list[SourceCitation]
    source_map: list[dict[str, Any]]

    # ── Error state ────────────────────────────────────────────────────────
    error_message: str
