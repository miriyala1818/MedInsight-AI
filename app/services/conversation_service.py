from __future__ import annotations
import uuid
from datetime import datetime, UTC
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from app.models.conversation import Conversation, Message


class ConversationService:
    def __init__(self, client: AsyncIOMotorClient) -> None:
        self._db = client["medical_research"]
        self._conversations_col = self._db["conversations"]
        self._messages_col = self._db["messages"]

    async def create_conversation(self, title: str | None = None) -> Conversation:
        """Create a new conversation"""
        conversation_data = {
            "_id": str(uuid.uuid4()),
            "title": title or "New Conversation",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await self._conversations_col.insert_one(conversation_data)
        return Conversation(**conversation_data)

    async def list_conversations(self, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        """List all conversations with pagination"""
        # Get total count
        total = await self._conversations_col.count_documents({})

        # Get conversations sorted by updated_at
        conversations = await self._conversations_col.find(
            {}
        ).sort("updated_at", -1).skip(offset).limit(limit).to_list(None)

        items = []
        for conv in conversations:
            # Count messages for this conversation
            msg_count = await self._messages_col.count_documents({"conversation_id": conv["_id"]})
            items.append({
                "id": conv["_id"],
                "title": conv["title"],
                "created_at": conv["created_at"],
                "updated_at": conv["updated_at"],
                "message_count": msg_count,
            })

        return items, total

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get conversation with all messages"""
        conv = await self._conversations_col.find_one({"_id": conversation_id})
        if not conv:
            return None

        messages = await self._messages_col.find(
            {"conversation_id": conversation_id}
        ).sort("created_at", 1).to_list(None)

        conv["messages"] = [Message(**msg) for msg in messages]
        return Conversation(**conv)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        confidence_score: float | None = None,
        citations: list[dict[str, Any]] | None = None,
        sources_used: list[str] | None = None,
    ) -> Message:
        """Add a message to a conversation"""
        message_data = {
            "_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "confidence_score": confidence_score,
            "citations": citations,
            "sources_used": sources_used,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await self._messages_col.insert_one(message_data)

        # Update conversation's updated_at and auto-title if first message
        conv = await self._conversations_col.find_one({"_id": conversation_id})
        if conv:
            update_data = {"updated_at": datetime.now(UTC)}
            if role == "user" and conv.get("title") == "New Conversation":
                update_data["title"] = content[:80].strip() + ("..." if len(content) > 80 else "")
            await self._conversations_col.update_one(
                {"_id": conversation_id},
                {"$set": update_data}
            )

        return Message(**message_data)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation and all its messages"""
        # Delete all messages
        await self._messages_col.delete_many({"conversation_id": conversation_id})
        # Delete conversation
        result = await self._conversations_col.delete_one({"_id": conversation_id})
        return result.deleted_count > 0

    async def update_conversation(self, conversation_id: str, title: str) -> Conversation | None:
        """Update conversation details"""
        result = await self._conversations_col.update_one(
            {"_id": conversation_id},
            {"$set": {"title": title, "updated_at": datetime.now(UTC)}}
        )
        if result.modified_count > 0 or result.matched_count > 0:
            return await self.get_conversation(conversation_id)
        return None
