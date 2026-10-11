from functools import lru_cache

from app.services.pubmed_service import PubMedService


@lru_cache(maxsize=1)
def get_pubmed_service() -> PubMedService:
    return PubMedService()
