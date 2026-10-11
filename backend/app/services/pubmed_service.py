from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.models.pubmed import PubMedArticle, PubMedSearchPage
from app.services.cache import TTLCache
from app.services.pubmed_client import PubMedClient, PubMedError


@dataclass(slots=True)
class PubMedQueryResult:
    query: str
    page: int
    page_size: int
    total_results: int
    articles: list[PubMedArticle]


class PubMedService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: PubMedClient | None = None,
        cache: TTLCache[Any] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or PubMedClient(self._settings)
        self._cache = cache or TTLCache[object](self._settings.pubmed_cache_ttl_seconds)

    async def search_articles(self, query: str, *, page: int = 1, page_size: int | None = None) -> PubMedSearchPage:
        page_size = page_size or self._settings.pubmed_page_size
        cache_key = self._build_cache_key(query, page, page_size)
        cached = self._cache.get(cache_key)
        if isinstance(cached, PubMedSearchPage):
            return cached

        search_payload = await self._client.search(query, page=page, page_size=page_size)
        articles = await self._retrieve_articles(search_payload.pmids)
        result = PubMedSearchPage(
            query=query,
            total_results=search_payload.total_results,
            page=page,
            page_size=page_size,
            articles=articles,
        )
        self._cache.set(cache_key, result)
        return result

    async def get_article_by_pmid(self, pmid: str) -> PubMedArticle:
        cache_key = self._build_article_cache_key(pmid)
        cached = self._cache.get(cache_key)
        if isinstance(cached, PubMedArticle):
            return cached

        article = PubMedArticle.model_validate(await self._client.fetch_article(pmid))
        self._cache.set(cache_key, article)
        return article

    async def get_articles_by_pmids(self, pmids: list[str]) -> list[PubMedArticle]:
        if not pmids:
            return []
        return await self._retrieve_articles(pmids)

    async def _retrieve_articles(self, pmids: list[str]) -> list[PubMedArticle]:
        results = await self._client.fetch_articles(pmids)
        articles = [PubMedArticle.model_validate(item) for item in results]
        for article in articles:
            self._cache.set(self._build_article_cache_key(article.pmid), article)
        return articles

    def _build_cache_key(self, query: str, page: int, page_size: int) -> str:
        return f"pubmed:search:{query.lower().strip()}:{page}:{page_size}"

    def _build_article_cache_key(self, pmid: str) -> str:
        return f"pubmed:article:{pmid.strip()}"


__all__ = ["PubMedClient", "PubMedError", "PubMedService", "PubMedQueryResult"]
