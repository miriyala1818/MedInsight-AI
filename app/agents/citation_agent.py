from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.grounding import GroundedStatement, GroundingCitation
from app.models.retrieval import RetrievedDocument


class CitationAgent(BaseAgent):
    """Formats grounded statements and retrieved documents into final citations."""

    agent_name = "citation"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        citations = self._build_citations(payload)
        return {
            "status": "answering",
            "next_step": "response",
            "citations": citations,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_citations(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Build citation dicts from two possible sources (in priority order):
        1. source_map from the ResponseAgent / HallucinationPreventionFramework
        2. retrieved_documents / evidence from the RetrievalAgent
        """
        # Try grounded source_map first (highest quality — per-statement citations)
        source_map = payload.get("source_map") or []
        if source_map:
            return self._citations_from_source_map(source_map)

        # Fall back to raw retrieved documents
        raw_documents = payload.get("retrieved_documents") or payload.get("evidence") or []
        if raw_documents:
            return self._citations_from_documents(raw_documents)

        return []

    def _citations_from_source_map(
        self, source_map: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Flatten grounded statements → unique citations, preserving relevance order."""
        seen_ids: set[str] = set()
        citations: list[dict[str, Any]] = []

        for entry in source_map:
            # entry may be a GroundedStatement dict or a raw dict with a 'citations' key
            raw_citations: list[dict[str, Any]] = entry.get("citations") or []
            for cite in raw_citations:
                # Build a dedup key from source + id
                dedup = f"{cite.get('source_name', '')}::{cite.get('source_id', '')}"
                if dedup in seen_ids:
                    continue
                seen_ids.add(dedup)
                citations.append(
                    {
                        "id": cite.get("source_id") or dedup,
                        "source": cite.get("source_name") or "Source",
                        "title": cite.get("title") or "Reference",
                        "url": cite.get("url") or "#",
                        "snippet": cite.get("snippet") or "",
                        "section": cite.get("section") or "Evidence",
                    }
                )

        return citations

    def _citations_from_documents(
        self, raw_documents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert raw RetrievedDocument dicts to the citation schema."""
        seen_ids: set[str] = set()
        citations: list[dict[str, Any]] = []

        for doc in raw_documents:
            source_name = doc.get("source_name") or "Source"
            source_id = doc.get("source_id") or ""
            dedup = f"{source_name}::{source_id}"
            if dedup in seen_ids:
                continue
            seen_ids.add(dedup)

            abstract = doc.get("abstract") or ""
            snippet = abstract[:220].rstrip() if abstract else ""

            citations.append(
                {
                    "id": source_id or dedup,
                    "source": source_name,
                    "title": doc.get("title") or "Reference",
                    "url": doc.get("url") or "#",
                    "snippet": snippet,
                    "section": doc.get("journal") or "Evidence",
                }
            )

        return citations
