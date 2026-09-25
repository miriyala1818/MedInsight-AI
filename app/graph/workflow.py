from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.planner_agent import PlannerAgent
from app.agents.response_agent import ResponseAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.citation_agent import CitationAgent
from app.core.config import get_settings
from app.graph.state import ResearchState
from app.services.llm_service import LLMService


MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 0.2


# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

async def _invoke_with_retry(
    agent_name: str,
    agent_call: Callable[[ResearchState], Awaitable[dict[str, Any]]],
    state: ResearchState,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    retry_counts = dict(state.get("retry_counts") or {})

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await agent_call(state)
            if not isinstance(result, dict):
                raise TypeError(f"{agent_name} must return a dict.")
            result.setdefault("retry_counts", retry_counts)
            result.setdefault("trace_id", state.get("trace_id") or str(uuid4()))
            return result
        except NotImplementedError:
            fallback.setdefault("retry_counts", retry_counts)
            fallback.setdefault("trace_id", state.get("trace_id") or str(uuid4()))
            return fallback
        except Exception as exc:
            retry_counts[agent_name] = attempt
            if attempt >= MAX_ATTEMPTS:
                import logging
                logging.getLogger(__name__).error(
                    "%s failed after %d attempts: %s", agent_name, MAX_ATTEMPTS, exc, exc_info=True
                )
                return {
                    "status": "error",
                    "error_message": f"{agent_name} failed: {exc}",
                    "answer": f"Error in {agent_name}: {exc}",
                    "retry_counts": retry_counts,
                    "trace_id": state.get("trace_id") or str(uuid4()),
                    "next_step": "response",
                }
            await asyncio.sleep(BASE_BACKOFF_SECONDS * attempt)

    return fallback


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

def _planner_fallback(state: ResearchState) -> dict[str, Any]:
    return {
        "status": "retrieving",
        "next_step": "retrieval",
        "entities": [],
        "information_needs": [state.get("question", "")],
    }

def _retrieval_fallback(state: ResearchState) -> dict[str, Any]:
    return {
        "status": "generating",
        "next_step": "generation",
        "retrieved_documents": [],
        "evidence": [],
    }

def _generation_fallback(state: ResearchState) -> dict[str, Any]:
    return {
        "status": "validating",
        "next_step": "validation",
        "answer": state.get("question", ""),
        "draft_answer": "",
        "confidence_score": 0,
        "confidence_level": "Low",
    }

def _validation_fallback(state: ResearchState) -> dict[str, Any]:
    return {
        "status": "citing",
        "next_step": "citation",
    }

def _citation_fallback(state: ResearchState) -> dict[str, Any]:
    return {
        "status": "answering",
        "next_step": "response",
        "citations": [],
    }

def _response_fallback(state: ResearchState) -> dict[str, Any]:
    answer = (
        state.get("answer")
        or state.get("draft_answer")
        or "Something went wrong. Please try again."
    )
    return {
        "status": "completed",
        "answer": answer,
        "citations": state.get("citations", []),
        "confidence_score": state.get("confidence_score", 0),
        "confidence_level": state.get("confidence_level", "Low"),
    }


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def planner_node(state: ResearchState) -> dict[str, Any]:
    return await _invoke_with_retry(
        "planner", PlannerAgent().run, state, _planner_fallback(state)
    )

async def retrieval_node(state: ResearchState) -> dict[str, Any]:
    return await _invoke_with_retry(
        "retrieval", RetrievalAgent().run, state, _retrieval_fallback(state)
    )

async def generation_node(state: ResearchState) -> dict[str, Any]:
    async def _generate(s: ResearchState) -> dict[str, Any]:
        question = str(s.get("question") or "")
        entities = s.get("entities") or []
        evidence = s.get("retrieved_documents") or s.get("evidence") or []
        conversation_history = s.get("conversation_history") or []
        settings = get_settings()
        llm = LLMService(settings)

        if not llm.is_configured:
            return {
                "status": "completed",
                "next_step": "response",
                "answer": "The LLM is not configured. Add LLM_API_KEY to backend/.env.",
                "draft_answer": "",
                "confidence_score": 0,
                "citations": [],
            }

        # Use grounded completion if evidence is available
        if evidence:
            completion = await llm.complete_grounded(question, evidence, conversation_history=conversation_history)
        else:
            completion = await llm.complete(question, context_entities=entities, conversation_history=conversation_history)
        
        return {
            "status": "validating",
            "next_step": "validation",
            "draft_answer": completion.content,
            "answer": completion.content,
            "confidence_score": 70,
            "confidence_level": "Medium",
        }

    return await _invoke_with_retry("generation", _generate, state, _generation_fallback(state))

async def validation_node(state: ResearchState) -> dict[str, Any]:
    return await _invoke_with_retry(
        "validation", ValidationAgent().run, state, _validation_fallback(state)
    )

async def citation_node(state: ResearchState) -> dict[str, Any]:
    return await _invoke_with_retry(
        "citation", CitationAgent().run, state, _citation_fallback(state)
    )

async def response_node(state: ResearchState) -> dict[str, Any]:
    return await _invoke_with_retry(
        "response", ResponseAgent().run, state, _response_fallback(state)
    )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_after_planner(state: ResearchState) -> str:
    next_step = state.get("next_step")

    # Planner pre-answered the message (off-topic redirect or empty input)
    if next_step == "response":
        return "response"

    # Planner wants to skip retrieval and go straight to generation
    # (greetings, short messages, casual questions)
    if next_step == "generation":
        return "generation"

    # Default: run full retrieval pipeline
    return "retrieval"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_research_workflow() -> Any:
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("generation", generation_node)
    graph.add_node("validation", validation_node)
    graph.add_node("citation", citation_node)
    graph.add_node("response", response_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "retrieval": "retrieval",
            "generation": "generation",
            "response": "response",
        },
    )
    graph.add_edge("retrieval", "generation")
    graph.add_edge("generation", "validation")
    graph.add_edge("validation", "citation")
    graph.add_edge("citation", "response")
    graph.add_edge("response", END)

    return graph.compile()
