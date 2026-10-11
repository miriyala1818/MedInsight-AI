from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus
import asyncio
import xml.etree.ElementTree as ET

import httpx

from app.core.config import Settings, get_settings


class PubMedError(RuntimeError):
    pass


@dataclass(slots=True)
class PubMedSearchPayload:
    pmids: list[str]
    total_results: int
    retstart: int
    retmax: int


class PubMedClient:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client

    @property
    def _base_url(self) -> str:
        return self._settings.ncbi_base_url.rstrip("/")

    def _common_params(self) -> dict[str, str]:
        params: dict[str, str] = {
            "tool": self._settings.ncbi_tool,
            "retmode": "xml",
        }
        if self._settings.ncbi_email:
            params["email"] = self._settings.ncbi_email
        if self._settings.ncbi_api_key:
            params["api_key"] = self._settings.ncbi_api_key
        return params

    async def __aenter__(self) -> "PubMedClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0)
        return self._client

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int | None = None,
    ) -> PubMedSearchPayload:
        page_size = page_size or self._settings.pubmed_page_size
        retstart = max(page - 1, 0) * page_size
        params = {
            **self._common_params(),
            "db": "pubmed",
            "term": query,
            "retstart": str(retstart),
            "retmax": str(page_size),
            "usehistory": "n",
        }

        try:
            response = await self.client.get(f"{self._base_url}/esearch.fcgi", params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PubMedError(f"PubMed search request failed: {exc}") from exc

        root = ET.fromstring(response.text)
        pmids = [node.text or "" for node in root.findall("./IdList/Id") if node.text]
        total_results = int(root.findtext("./Count") or "0")
        return PubMedSearchPayload(pmids=pmids, total_results=total_results, retstart=retstart, retmax=page_size)

    async def fetch_article(self, pmid: str) -> dict[str, Any]:
        params = {
            **self._common_params(),
            "db": "pubmed",
            "id": pmid,
            "rettype": "abstract",
            "retmode": "xml",
        }

        try:
            response = await self.client.get(f"{self._base_url}/efetch.fcgi", params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PubMedError(f"PubMed article fetch failed for PMID {pmid}: {exc}") from exc

        return self._parse_efetch_xml(response.text)

    async def fetch_articles(self, pmids: list[str]) -> list[dict[str, Any]]:
        if not pmids:
            return []
        results = await asyncio.gather(*(self.fetch_article(pmid) for pmid in pmids))
        return list(results)

    def _parse_efetch_xml(self, xml_text: str) -> dict[str, Any]:
        root = ET.fromstring(xml_text)
        article = root.find(".//PubmedArticle")
        if article is None:
            raise PubMedError("PubMed response did not contain an article record.")

        citation = article.find("./MedlineCitation")
        article_node = article.find("./MedlineCitation/Article")
        if citation is None or article_node is None:
            raise PubMedError("PubMed article payload was missing citation data.")

        pmid = citation.findtext("./PMID") or ""
        title = _normalize_text(article_node.findtext("./ArticleTitle"))
        journal = _normalize_text(article_node.findtext("./Journal/Title"))
        publication_date = _extract_publication_date(article_node)
        abstract = _extract_abstract(article_node)
        authors = _extract_authors(article_node)
        url = f"https://pubmed.ncbi.nlm.nih.gov/{quote_plus(pmid)}/" if pmid else ""

        return {
            "title": title,
            "authors": authors,
            "journal": journal,
            "publication_date": publication_date,
            "abstract": abstract,
            "pmid": pmid,
            "url": url,
        }


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(part.strip() for part in value.split())


def _extract_authors(article_node: ET.Element) -> list[str]:
    authors: list[str] = []
    for author in article_node.findall("./AuthorList/Author"):
        collective = _normalize_text(author.findtext("./CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        last_name = _normalize_text(author.findtext("./LastName"))
        fore_name = _normalize_text(author.findtext("./ForeName"))
        initials = _normalize_text(author.findtext("./Initials"))
        name = " ".join(part for part in [fore_name, last_name] if part)
        if not name and initials and last_name:
            name = f"{last_name} {initials}"
        if name:
            authors.append(name)
    return authors


def _extract_abstract(article_node: ET.Element) -> str:
    abstract_nodes = article_node.findall("./Abstract/AbstractText")
    if not abstract_nodes:
        return ""
    chunks: list[str] = []
    for node in abstract_nodes:
        label = node.attrib.get("Label") or node.attrib.get("NlmCategory")
        text = _normalize_text("".join(node.itertext()))
        if label and text:
            chunks.append(f"{label}: {text}")
        elif text:
            chunks.append(text)
    return "\n".join(chunks)


def _extract_publication_date(article_node: ET.Element) -> str:
    journal_issue = article_node.find("./Journal/JournalIssue/PubDate")
    if journal_issue is not None:
        year = _normalize_text(journal_issue.findtext("./Year"))
        month = _normalize_text(journal_issue.findtext("./Month"))
        day = _normalize_text(journal_issue.findtext("./Day"))
        medline_date = _normalize_text(journal_issue.findtext("./MedlineDate"))
        if medline_date:
            return medline_date
        parts = [part for part in [year, month, day] if part]
        if parts:
            return "-".join(parts)
    pub_date = _normalize_text(article_node.findtext("./ArticleDate/Year"))
    if pub_date:
        month = _normalize_text(article_node.findtext("./ArticleDate/Month"))
        day = _normalize_text(article_node.findtext("./ArticleDate/Day"))
        parts = [part for part in [pub_date, month, day] if part]
        return "-".join(parts)
    return ""
