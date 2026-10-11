from __future__ import annotations

import asyncio
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.models.retrieval import RetrievedDocument, SourceRetrievalResponse, SourceMetadata
from app.services.cache import TTLCache
from app.services.source_adapters import (
    AdapterSearchResult,
    BaseSourceAdapter,
    ClinicalTrialsSourceAdapter,
    DisabledSourceAdapter,
    EuropePMCSourceAdapter,
    OpenFDASourceAdapter,
    PubMedSourceAdapter,
)


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


@dataclass(slots=True)
class SourceRetrievalSummary:
    query: str
    page: int
    page_size: int
    sources_used: list[str]
    results: list[RetrievedDocument]


class SourceRetriever:
    def __init__(
        self,
        settings: Settings | None = None,
        adapters: Sequence[BaseSourceAdapter] | None = None,
        cache: TTLCache[Any] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._adapters = list(adapters or self._build_default_adapters())
        self._cache = cache or TTLCache[Any](self._settings.pubmed_cache_ttl_seconds)

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 10,
        sources: Sequence[str] | None = None,
    ) -> SourceRetrievalResponse:
        cache_key = self._build_cache_key(query, page, page_size, sources)
        cached = self._cache.get(cache_key)
        if isinstance(cached, SourceRetrievalResponse):
            return cached

        selected_adapters = self._select_adapters(sources)
        if not selected_adapters:
            response = SourceRetrievalResponse(query=query, page=page, page_size=page_size)
            self._cache.set(cache_key, response)
            return response

        results_by_source = await self._search_sources(query, selected_adapters, page=page, page_size=page_size)
        merged = self.merge_results(results_by_source)
        deduplicated = self.deduplicate(merged)
        ranked = self.rank(deduplicated, query=query)
        limited = ranked[:page_size]
        response = SourceRetrievalResponse(
            query=query,
            page=page,
            page_size=page_size,
            total_results=len(ranked),
            results=limited,
            sources_used=[adapter.source_name for adapter in selected_adapters],
        )
        self._cache.set(cache_key, response)
        return response

    def rank(self, results: list[RetrievedDocument], query: str | None = None) -> list[RetrievedDocument]:
        tokens = self._tokenize(query or "")
        ranked: list[RetrievedDocument] = []
        for result in results:
            score = self._score_result(result, tokens)
            ranked.append(result.model_copy(update={"score": score}))
        ranked.sort(key=lambda item: (-item.score, item.publication_date, item.title.lower()))
        return ranked

    def merge_results(
        self,
        results_by_source: Mapping[str, list[RetrievedDocument]] | Sequence[AdapterSearchResult],
    ) -> list[RetrievedDocument]:
        merged: list[RetrievedDocument] = []
        if isinstance(results_by_source, Mapping):
            for items in results_by_source.values():
                merged.extend(items)
            return merged

        for result in results_by_source:
            merged.extend(result.items)
        return merged

    def deduplicate(self, results: Sequence[RetrievedDocument]) -> list[RetrievedDocument]:
        best_by_key: dict[str, RetrievedDocument] = {}
        for result in results:
            key = self._dedupe_key(result)
            existing = best_by_key.get(key)
            if existing is None or result.score > existing.score:
                best_by_key[key] = result
        return list(best_by_key.values())

    async def _search_sources(
        self,
        query: str,
        adapters: Sequence[BaseSourceAdapter],
        *,
        page: int,
        page_size: int,
    ) -> list[AdapterSearchResult]:
        semaphore = asyncio.Semaphore(self._settings.source_retrieval_parallelism)

        async def guarded_search(adapter: BaseSourceAdapter) -> AdapterSearchResult:
            async with semaphore:
                try:
                    return await adapter.search(query, page=page, page_size=page_size)
                except Exception:
                    return AdapterSearchResult(items=[], total_results=0, metadata={"source": adapter.source_name, "error": True})

        return await asyncio.gather(*(guarded_search(adapter) for adapter in adapters))

    def _select_adapters(self, sources: Sequence[str] | None) -> list[BaseSourceAdapter]:
        if sources is None:
            return list(self._adapters)
        requested = {source.strip().lower() for source in sources}
        return [adapter for adapter in self._adapters if adapter.source_name.lower() in requested]

    def _build_default_adapters(self) -> list[BaseSourceAdapter]:
        return [
            PubMedSourceAdapter(),
            EuropePMCSourceAdapter(),
            ClinicalTrialsSourceAdapter(),
            OpenFDASourceAdapter(),
        ]

    def _build_cache_key(
        self,
        query: str,
        page: int,
        page_size: int,
        sources: Sequence[str] | None,
    ) -> str:
        source_key = ",".join(sorted(source.lower() for source in sources)) if sources else "all"
        return f"source-search:{query.lower().strip()}:{page}:{page_size}:{source_key}"

    def _score_result(self, result: RetrievedDocument, query_tokens: Sequence[str]) -> float:
        source_weight = self._settings.source_authority_weights.get(result.source_name, 0.75)
        title_tokens = self._tokenize(result.title)
        abstract_tokens = self._tokenize(result.abstract)
        journal_tokens = self._tokenize(result.journal)

        overlap = self._weighted_overlap(query_tokens, title_tokens, abstract_tokens, journal_tokens)
        recency = self._recency_boost(result.publication_date)
        completeness = 0.1 if result.abstract else 0.0

        score = (source_weight * 0.5) + (overlap * 0.35) + (recency * 0.1) + completeness
        return round(min(score, 1.0), 4)

    def _weighted_overlap(
        self,
        query_tokens: Sequence[str],
        title_tokens: Sequence[str],
        abstract_tokens: Sequence[str],
        journal_tokens: Sequence[str],
    ) -> float:
        if not query_tokens:
            return 0.0
        query_set = set(query_tokens)
        title_hit = len(query_set & set(title_tokens))
        abstract_hit = len(query_set & set(abstract_tokens))
        journal_hit = len(query_set & set(journal_tokens))
        total = (title_hit * 2.0) + abstract_hit + (journal_hit * 0.5)
        return min(total / max(len(query_set) * 2.5, 1.0), 1.0)

    def _recency_boost(self, publication_date: str) -> float:
        if not publication_date:
            return 0.0
        match = re.search(r"(19|20)\d{2}", publication_date)
        if match is None:
            return 0.0
        year = int(match.group(0))
        current_year = datetime.now(UTC).year
        age = max(current_year - year, 0)
        if age == 0:
            return 1.0
        return max(0.0, 1.0 - min(age / 20.0, 1.0))

    def _dedupe_key(self, result: RetrievedDocument) -> str:
        if result.source_id:
            return f"{result.source_name.lower()}::{result.source_id.lower()}"
        if result.url:
            return f"url::{result.url.lower()}"
        normalized_title = self._normalize_whitespace(result.title).lower()
        normalized_date = self._normalize_whitespace(result.publication_date).lower()
        return f"title::{normalized_title}::{normalized_date}"

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text or "")]

    def _normalize_whitespace(self, text: str) -> str:
        return " ".join(text.split())


__all__ = [
    "SourceRetriever",
    "SourceRetrievalSummary",
    "RetrievedDocument",
    "SourceMetadata",
]
