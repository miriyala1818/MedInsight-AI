from __future__ import annotations

from typing import Any

import httpx

from app.models.retrieval import RetrievedDocument, SourceMetadata


class EuropePMCClient:
    """Client for the Europe PMC REST API — covers Nature, Lancet, BMJ and other major journals."""

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    SOURCE_NAME = "Europe PMC"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def search(self, query: str, *, page_size: int = 10) -> list[RetrievedDocument]:
        """Search Europe PMC for articles matching the query."""
        params = {
            "query": query,
            "resultType": "core",
            "pageSize": min(page_size, 25),
            "format": "json",
            "sort": "RELEVANCE",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self.BASE_URL}/search", params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        results = data.get("resultList", {}).get("result", [])
        documents: list[RetrievedDocument] = []

        for article in results:
            try:
                doc = self._parse_article(article, query, page_size)
                documents.append(doc)
            except Exception:
                continue

        return documents

    def _parse_article(self, article: dict[str, Any], query: str, page_size: int) -> RetrievedDocument:
        authors = []
        author_list = article.get("authorList", {}).get("author", [])
        for author in author_list[:5]:  # Limit to first 5 authors
            full_name = author.get("fullName") or ""
            if full_name:
                authors.append(full_name)

        pmid = article.get("pmid") or ""
        doi = article.get("doi") or ""
        source_id = pmid or doi or article.get("id", "")

        url = ""
        if pmid:
            url = f"https://europepmc.org/article/MED/{pmid}"
        elif doi:
            url = f"https://doi.org/{doi}"

        return RetrievedDocument(
            source_name=self.SOURCE_NAME,
            source_id=str(source_id),
            title=article.get("title") or "Untitled",
            authors=authors,
            journal=article.get("journalTitle") or article.get("journalInfo", {}).get("journal", {}).get("title", ""),
            publication_date=article.get("firstPublicationDate") or "",
            abstract=article.get("abstractText") or "",
            url=url,
            metadata=SourceMetadata(
                source_name=self.SOURCE_NAME,
                adapter_name="EuropePMCSourceAdapter",
                query=query,
                page_size=page_size,
            ),
        )
