from __future__ import annotations

from typing import Any

import httpx

from app.models.retrieval import RetrievedDocument, SourceMetadata


class OpenFDAClient:
    """Client for the OpenFDA Drug Labeling API."""

    LABEL_URL = "https://api.fda.gov/drug/label.json"
    SOURCE_NAME = "OpenFDA"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def search(self, query: str, *, page_size: int = 5) -> list[RetrievedDocument]:
        """Search OpenFDA drug labels for information matching the query."""
        # OpenFDA uses a specific search syntax
        search_term = f'"{query}"'
        params = {
            "search": search_term,
            "limit": min(page_size, 10),
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self.LABEL_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        results = data.get("results", [])
        documents: list[RetrievedDocument] = []

        for label in results:
            try:
                doc = self._parse_label(label, query, page_size)
                if doc:
                    documents.append(doc)
            except Exception:
                continue

        return documents

    def _parse_label(self, label: dict[str, Any], query: str, page_size: int) -> RetrievedDocument | None:
        openfda = label.get("openfda", {})
        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])
        manufacturer = openfda.get("manufacturer_name", [])
        spl_id = openfda.get("spl_id", [""])

        title_parts = []
        if brand_names:
            title_parts.append(brand_names[0])
        if generic_names:
            title_parts.append(f"({generic_names[0]})")

        title = " ".join(title_parts) if title_parts else "Unknown Drug"
        if title == "Unknown Drug":
            return None  # Skip entries without identifiable drug names

        # Build abstract from drug label sections
        abstract_parts = []

        indications = label.get("indications_and_usage", [])
        if indications:
            abstract_parts.append(f"Indications: {indications[0][:400]}")

        warnings = label.get("warnings", []) or label.get("warnings_and_cautions", [])
        if warnings:
            abstract_parts.append(f"Warnings: {warnings[0][:300]}")

        adverse = label.get("adverse_reactions", [])
        if adverse:
            abstract_parts.append(f"Adverse Reactions: {adverse[0][:300]}")

        dosage = label.get("dosage_and_administration", [])
        if dosage:
            abstract_parts.append(f"Dosage: {dosage[0][:300]}")

        source_id = spl_id[0] if spl_id else ""
        url = f"https://labels.fda.gov/getlabel?id={source_id}" if source_id else "https://www.fda.gov"

        return RetrievedDocument(
            source_name=self.SOURCE_NAME,
            source_id=source_id,
            title=title,
            authors=manufacturer[:2] if manufacturer else [],
            journal="FDA Drug Labels",
            publication_date=label.get("effective_time", ""),
            abstract="\n".join(abstract_parts),
            url=url,
            metadata=SourceMetadata(
                source_name=self.SOURCE_NAME,
                adapter_name="OpenFDASourceAdapter",
                query=query,
                page_size=page_size,
            ),
        )
