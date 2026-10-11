from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.config import AppConfigResponse

router = APIRouter(prefix="/config")


@router.get("", response_model=AppConfigResponse, summary="Application configuration")
async def get_app_config(settings: Settings = Depends(get_settings)) -> AppConfigResponse:
    return AppConfigResponse(
        llm_configured=bool(settings.llm_api_key),
        llm_model=settings.llm_model,
        trusted_sources=settings.trusted_sources,
        app_name=settings.app_name,
        version=settings.app_version,
    )
