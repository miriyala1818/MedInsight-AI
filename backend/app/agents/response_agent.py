from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class ResponseAgent(BaseAgent):
    """
    Finalises the answer and formats it for the API response.

    With evidence retrieval disabled this is a thin pass-through.
    When retrieval is re-enabled, this is where grounding / hallucination
    checking will run again.
    """

    agent_name = "response"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Prefer draft_answer (from generation node), fall back to answer already in state
        answer = str(
            payload.get("draft_answer") or payload.get("answer") or ""
        ).strip()

        if not answer:
            answer = "I couldn't generate a response. Please try rephrasing your question."

        return {
            "status": "completed",
            "answer": answer,
            "confidence_score": payload.get("confidence_score", 0),
            "confidence_level": payload.get("confidence_level", "Low"),
            "citations": payload.get("citations", []),
            "source_map": payload.get("source_map", []),
        }
