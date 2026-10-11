from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class PubMedArticle(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    journal: str = ""
    publication_date: str = ""
    abstract: str = ""
    pmid: str = ""
    url: HttpUrl | str = ""


class PubMedSearchResult(BaseModel):
    pmid: str
    title: str = ""


class PubMedSearchPage(BaseModel):
    query: str
    total_results: int
    page: int
    page_size: int
    articles: list[PubMedArticle]
