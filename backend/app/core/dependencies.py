from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient
from qdrant_client import QdrantClient

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.evaluation_service import EvaluationService
from app.services.pubmed_dependencies import get_pubmed_service
from app.services.query_service import ResearchQueryService
from app.services.source_retriever import SourceRetriever
from app.services.conversation_service import ConversationService


def get_qdrant_client(settings: Settings = Depends(get_settings)) -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


async def get_db_session(
    db: AsyncIOMotorClient = Depends(get_db),
) -> AsyncIterator[AsyncIOMotorClient]:
    yield db


def get_research_query_service(settings: Settings = Depends(get_settings)) -> ResearchQueryService:
    return ResearchQueryService(settings=settings)


def get_pubmed_research_service():
    return get_pubmed_service()


def get_source_retriever() -> SourceRetriever:
    return SourceRetriever()


@lru_cache(maxsize=1)
def get_evaluation_service() -> EvaluationService:
    return EvaluationService()


def get_conversation_service(client: AsyncIOMotorClient = Depends(get_db_session)) -> ConversationService:
    return ConversationService(client)
