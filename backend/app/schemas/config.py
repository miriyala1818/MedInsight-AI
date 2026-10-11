from pydantic import BaseModel


class AppConfigResponse(BaseModel):
    llm_configured: bool
    llm_model: str
    trusted_sources: list[str]
    app_name: str
    version: str
