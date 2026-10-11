from fastapi import APIRouter

from app.api.v1.config import router as config_router
from app.api.v1.health import router as health_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.query import router as query_router
from app.api.v1.conversations import router as conversations_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(config_router, tags=["config"])
api_router.include_router(query_router, tags=["queries"])
api_router.include_router(evaluation_router, tags=["evaluation"])
api_router.include_router(conversations_router, tags=["conversations"])
