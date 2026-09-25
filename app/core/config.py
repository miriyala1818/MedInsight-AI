from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file (backend/app/core/config.py → backend/.env)
# This ensures the correct .env is loaded regardless of the working directory
# when uvicorn/the server is started.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
_ENV_LOCAL_FILE = _BACKEND_DIR / ".env.local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ENV_FILE), str(_ENV_LOCAL_FILE)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Medical Research Assistant")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="local")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    api_v1_prefix: str = Field(default="/api/v1")
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # MongoDB connection
    mongodb_url: str = Field(
        default="mongodb+srv://notkind420_db_user:Z2M1DQkBwarlw7u8@cluster0.muajv0q.mongodb.net/?appName=Cluster0"
    )
    mongodb_db_name: str = Field(default="medical_research")

    # Qdrant (Vector DB)
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str = Field(default="")
    qdrant_collection: str = Field(default="medical_knowledge")

    # LLM Settings
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="https://generativelanguage.googleapis.com/v1beta/openai")
    llm_model: str = Field(default="gemini-2.0-flash-lite")
    llm_timeout_seconds: int = Field(default=60, ge=1)

    # NCBI / PubMed
    ncbi_base_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils")
    ncbi_tool: str = Field(default="medical-research-assistant")
    ncbi_email: str | None = Field(default=None)
    ncbi_api_key: str | None = Field(default=None)

    # Agent Settings
    trusted_sources: list[str] = Field(
        default_factory=lambda: ["PubMed", "Europe PMC", "ClinicalTrials.gov", "OpenFDA"]
    )
    source_authority_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "PubMed": 1.0,
            "Europe PMC": 0.95,
            "ClinicalTrials.gov": 0.9,
            "OpenFDA": 0.85
        }
    )

    # Retrieval Settings
    pubmed_page_size: int = Field(default=10, ge=1, le=100)
    pubmed_cache_ttl_seconds: int = Field(default=900, ge=1)
    source_retrieval_parallelism: int = Field(default=4, ge=1, le=16)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Clear the cached settings and reload from .env — useful after editing .env without restarting."""
    get_settings.cache_clear()
    return get_settings()
