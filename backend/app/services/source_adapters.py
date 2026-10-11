from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.models.pubmed import PubMedArticle
from app.models.retrieval import RetrievedDocument, SourceMetadata
from app.services.pubmed_service import PubMedService


@dataclass(slots=True)
class AdapterSearchResult:
    items: list[RetrievedDocument]
    total_results: int = 0
    metadata: dict[str, Any] | None = None


class BaseSourceAdapter(ABC):
    source_name: str

    @abstractmethod
    async def search(self, query: str, *, page: int = 1, page_size: int = 10) -> AdapterSearchResult:
        raise NotImplementedError


class PubMedSourceAdapter(BaseSourceAdapter):
    source_name = "PubMed"

    def __init__(self, service: PubMedService | None = None) -> None:
        self._service = service or PubMedService()

    async def search(self, query: str, *, page: int = 1, page_size: int = 10) -> AdapterSearchResult:
        page_result = await self._service.search_articles(query, page=page, page_size=page_size)
        items = [
            RetrievedDocument(
                source_name=self.source_name,
                source_id=article.pmid,
                title=article.title,
                authors=article.authors,
                journal=article.journal,
                publication_date=article.publication_date,
                abstract=article.abstract,
                url=str(article.url),
                metadata=SourceMetadata(
                    source_name=self.source_name,
                    adapter_name=self.__class__.__name__,
                    query=query,
                    page=page,
                    page_size=page_size,
                    total_results=page_result.total_results,
                    raw={"pmid": article.pmid},
                ),
            )
            for article in page_result.articles
        ]
        return AdapterSearchResult(items=items, total_results=page_result.total_results)


class DisabledSourceAdapter(BaseSourceAdapter):
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    async def search(self, query: str, *, page: int = 1, page_size: int = 10) -> AdapterSearchResult:
        return AdapterSearchResult(items=[], total_results=0, metadata={"disabled": True, "source": self.source_name})


class EuropePMCSourceAdapter(BaseSourceAdapter):
    """Adapter for Europe PMC — covers Nature, Lancet, BMJ and major journals."""
    source_name = "Europe PMC"

    def __init__(self) -> None:
        from app.services.europepmc_client import EuropePMCClient
        self._client = EuropePMCClient()

    async def search(self, query: str, *, page: int = 1, page_size: int = 10) -> AdapterSearchResult:
        documents = await self._client.search(query, page_size=page_size)
        return AdapterSearchResult(items=documents, total_results=len(documents))


class ClinicalTrialsSourceAdapter(BaseSourceAdapter):
    """Adapter for ClinicalTrials.gov — NIH clinical trials database."""
    source_name = "ClinicalTrials.gov"

    def __init__(self) -> None:
        from app.services.clinicaltrials_client import ClinicalTrialsClient
        self._client = ClinicalTrialsClient()

    async def search(self, query: str, *, page: int = 1, page_size: int = 10) -> AdapterSearchResult:
        documents = await self._client.search(query, page_size=page_size)
        return AdapterSearchResult(items=documents, total_results=len(documents))


class OpenFDASourceAdapter(BaseSourceAdapter):
    """Adapter for OpenFDA — FDA drug labeling and adverse events."""
    source_name = "OpenFDA"

    def __init__(self) -> None:
        from app.services.openfda_client import OpenFDAClient
        self._client = OpenFDAClient()

    async def search(self, query: str, *, page: int = 1, page_size: int = 5) -> AdapterSearchResult:
        documents = await self._client.search(query, page_size=page_size)
        return AdapterSearchResult(items=documents, total_results=len(documents))
