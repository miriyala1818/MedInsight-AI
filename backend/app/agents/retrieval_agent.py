from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.services.source_retriever import SourceRetriever


class RetrievalAgent(BaseAgent):
    """Searches trusted sources and populates retrieved_documents in state."""

    agent_name = "retrieval"

    def __init__(self, retriever: SourceRetriever | None = None) -> None:
        self._retriever = retriever or SourceRetriever()

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Prefer the structured retrieval_query from the planner;
        # fall back to the raw question if the planner wasn't run.
        query = (
            str(payload.get("retrieval_query") or "").strip()
            or str(payload.get("question") or "").strip()
        )

        if not query:
            return {
                "status": "validating",
                "next_step": "validation",
                "retrieved_documents": [],
                "evidence": [],
            }

        settings = get_settings()
        page_size = settings.pubmed_page_size

        try:
            response = await self._retriever.search(query, page=1, page_size=page_size)
            documents = response.results
        except Exception as exc:
            # Surface the error but don't crash the pipeline; validation will abstain
            return {
                "status": "validating",
                "next_step": "validation",
                "retrieved_documents": [],
                "evidence": [],
                "error_message": f"Retrieval failed: {exc}",
            }

        # Serialise to plain dicts so LangGraph state stays JSON-serialisable
        serialised = [doc.model_dump() for doc in documents]

        return {
            "status": "validating",
            "next_step": "validation",
            "retrieved_documents": serialised,
            # Keep a separate "evidence" key for backward-compat with ResponseAgent
            "evidence": serialised,
            "sources_used": response.sources_used,
        }
