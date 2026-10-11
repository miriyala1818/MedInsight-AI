from fastapi import APIRouter, Depends

from app.core.dependencies import get_settings
from app.core.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health")


@router.get("", response_model=HealthResponse, summary="Health check")
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        version=settings.app_version,
    )
