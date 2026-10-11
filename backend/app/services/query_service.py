from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.graph.workflow import build_research_workflow
from app.schemas.query import QueryResponse
from app.services.llm_service import LLMService


class ResearchQueryService:
    """
    Orchestrates the multi-agent LangGraph workflow.

    Current flow (evidence retrieval temporarily disabled):
        Planner → Generation (LLM) → Response

    Planner classifies intent and extracts medical entities.
    Generation calls the LLM with those entities as context hints.
    Response finalises the answer for the API.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm_service or LLMService(self._settings)
        # Compile the LangGraph workflow once — it's stateless and thread-safe
        self._workflow = build_research_workflow()

    async def ask(self, question: str, session_id: str | None = None, conversation_history: list[dict[str, str]] | None = None) -> QueryResponse:
        """Run the full agent pipeline with conversation context and return a grounded, cited answer."""
        trace_id = session_id or str(uuid4())
        request_id = str(uuid4())

        initial_state: dict[str, Any] = {
            "question": question,
            "session_id": session_id,
            "conversation_history": conversation_history or [],
            "trace_id": trace_id,
            "request_id": request_id,
            "status": "planning",
            "retry_counts": {},
            "entities": [],
            "information_needs": [],
            "retrieved_documents": [],
            "evidence": [],
            "sources_used": [],
            "validation_summary": {},
            "contradictions_found": False,
            "is_supported": True,
            "explanation": "",
            "evidence_score": 0.0,
            "contradictions": [],
            "abstain_reason": "",
            "answer": "",
            "draft_answer": "",
            "confidence_score": 0.0,
            "confidence_level": "Low",
            "citations": [],
            "source_map": [],
            "error_message": "",
        }

        final_state: dict[str, Any] = await self._workflow.ainvoke(initial_state)

        answer = self._extract_answer(final_state, question)
        confidence = self._extract_confidence(final_state)
        citations = self._extract_citations(final_state)
        sources_used = final_state.get("sources_used") or []

        return QueryResponse(
            answer=answer,
            confidence_score=float(confidence),
            citations=citations,
            request_id=request_id,
            trace_id=trace_id,
            sources_used=sources_used,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_answer(self, state: dict[str, Any], original_question: str) -> str:
        answer = str(state.get("answer") or "").strip()

        if not answer and state.get("status") == "error":
            error_msg = state.get("error_message", "")
            return (
                f"The research pipeline encountered an error: {error_msg}"
                if error_msg
                else "The research pipeline encountered an error. Please try again."
            )

        return answer or (
            "No results were found for your query. "
            "Please try rephrasing with more specific medical terms."
        )

    def _extract_confidence(self, state: dict[str, Any]) -> float:
        raw = state.get("confidence_score")
        if raw is None:
            return 0.0
        try:
            # ValidationAgent and GroundedResponse both use 0–100 integer scale.
            # Return as-is so the frontend ConfidenceBadge receives the correct range.
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _extract_citations(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        citations = state.get("citations")
        if not citations:
            return []

        # Ensure citations are plain dicts (they might be TypedDicts or Pydantic models)
        result: list[dict[str, Any]] = []
        for c in citations:
            if isinstance(c, dict):
                result.append(c)
            elif hasattr(c, "model_dump"):
                result.append(c.model_dump())
            elif hasattr(c, "__dict__"):
                result.append(dict(c.__dict__))
        return result
