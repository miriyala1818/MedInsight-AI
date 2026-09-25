from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.dependencies import get_db_session
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    MessageCreate,
    MessageResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations")


def _get_service(client: AsyncIOMotorClient = Depends(get_db_session)) -> ConversationService:
    return ConversationService(client)


@router.get("", response_model=ConversationListResponse, summary="List conversations")
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    service: ConversationService = Depends(_get_service),
) -> ConversationListResponse:
    items, total = await service.list_conversations(limit=limit, offset=offset)
    return ConversationListResponse(
        conversations=[ConversationSummary(**item) for item in items],
        total=total,
    )


@router.post("", response_model=ConversationDetail, summary="Create a conversation", status_code=201)
async def create_conversation(
    body: ConversationCreate | None = None,
    service: ConversationService = Depends(_get_service),
) -> ConversationDetail:
    title = body.title if body else None
    conv = await service.create_conversation(title=title)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )


@router.get("/{conversation_id}", response_model=ConversationDetail, summary="Get a conversation with all messages")
async def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(_get_service),
) -> ConversationDetail:
    conv = await service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                confidence_score=msg.confidence_score,
                citations=msg.citations,
                sources_used=msg.sources_used,
                created_at=msg.created_at,
            )
            for msg in conv.messages
        ],
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, summary="Add a message to a conversation", status_code=201)
async def add_message(
    conversation_id: str,
    body: MessageCreate,
    service: ConversationService = Depends(_get_service),
) -> MessageResponse:
    message = await service.add_message(
        conversation_id=conversation_id,
        role=body.role,
        content=body.content,
        confidence_score=body.confidence_score,
        citations=body.citations,
        sources_used=body.sources_used,
    )
    if not message:
        raise HTTPException(status_code=404, detail="Could not add message")
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        confidence_score=message.confidence_score,
        citations=message.citations,
        sources_used=message.sources_used,
        created_at=message.created_at,
    )


@router.delete("/{conversation_id}", summary="Delete a conversation and all messages", status_code=204)
async def delete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(_get_service),
) -> None:
    deleted = await service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

@router.patch("/{conversation_id}", response_model=ConversationDetail, summary="Update a conversation")
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    service: ConversationService = Depends(_get_service),
) -> ConversationDetail:
    if not body.title:
        raise HTTPException(status_code=400, detail="Title is required")
    conv = await service.update_conversation(conversation_id, body.title)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                confidence_score=msg.confidence_score,
                citations=msg.citations,
                sources_used=msg.sources_used,
                created_at=msg.created_at,
            )
            for msg in conv.messages
        ] if hasattr(conv, 'messages') else [],
    )
