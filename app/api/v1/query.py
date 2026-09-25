from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.dependencies import get_db_session, get_research_query_service
from app.schemas.query import QueryRequest, QueryResponse
from app.services.conversation_service import ConversationService
from app.services.query_service import ResearchQueryService

router = APIRouter(prefix="/query")


@router.post("", response_model=QueryResponse, summary="Submit a medical research query")
async def submit_query(
    request: QueryRequest,
    service: ResearchQueryService = Depends(get_research_query_service),
    client: AsyncIOMotorClient = Depends(get_db_session),
) -> QueryResponse:
    conversation_id = request.conversation_id
    conv_service = ConversationService(client)

    # Auto-create conversation if not provided
    try:
        if not conversation_id:
            conv = await conv_service.create_conversation(title=request.question[:80])
            conversation_id = conv.id

        # Save user message
        await conv_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.question,
        )
    except Exception:
        # Don't break the query if conversation storage fails
        conversation_id = None

    # Retrieve conversation history for context
    conversation_history = []
    if conversation_id:
        try:
            conv = await conv_service.get_conversation(conversation_id)
            if conv and conv.messages:
                # Format previous messages for LLM context (exclude current message we just added)
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in conv.messages[:-1]  # Exclude the user message we just added
                ]
        except Exception:
            pass

    # Run the AI pipeline with conversation context
    result = await service.ask(request.question, session_id=request.session_id, conversation_history=conversation_history)

    # Save assistant message
    if conversation_id:
        try:
            await conv_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=result.answer,
                confidence_score=result.confidence_score,
                citations=result.citations,
                sources_used=result.sources_used,
            )
        except Exception:
            pass

    return QueryResponse(
        answer=result.answer,
        confidence_score=result.confidence_score,
        citations=result.citations,
        request_id=result.request_id,
        trace_id=result.trace_id,
        conversation_id=conversation_id,
        sources_used=result.sources_used,
    )
