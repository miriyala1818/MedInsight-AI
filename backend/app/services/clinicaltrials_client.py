from __future__ import annotations

from typing import Any

import httpx

from app.models.retrieval import RetrievedDocument, SourceMetadata


class ClinicalTrialsClient:
    """Client for the ClinicalTrials.gov API v2."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    SOURCE_NAME = "ClinicalTrials.gov"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def search(self, query: str, *, page_size: int = 10) -> list[RetrievedDocument]:
        """Search ClinicalTrials.gov for studies matching the query."""
        params = {
            "query.term": query,
            "pageSize": min(page_size, 20),
            "format": "json",
            "sort": "LastUpdatePostDate:desc",
            "fields": "NCTId,BriefTitle,OfficialTitle,BriefSummary,Condition,InterventionName,OverallStatus,Phase,StartDate,PrimaryCompletionDate,EnrollmentCount,LeadSponsorName",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        studies = data.get("studies", [])
        documents: list[RetrievedDocument] = []

        for study in studies:
            try:
                doc = self._parse_study(study, query, page_size)
                documents.append(doc)
            except Exception:
                continue

        return documents

    def _parse_study(self, study: dict[str, Any], query: str, page_size: int) -> RetrievedDocument:
        protocol = study.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        description_module = protocol.get("descriptionModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        interventions_module = protocol.get("armsInterventionsModule", {})
        design_module = protocol.get("designModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

        nct_id = id_module.get("nctId", "")
        title = id_module.get("officialTitle") or id_module.get("briefTitle") or "Untitled Study"
        brief_summary = description_module.get("briefSummary", "")

        # Build abstract from available fields
        parts = []
        if brief_summary:
            parts.append(brief_summary)

        status = status_module.get("overallStatus", "")
        if status:
            parts.append(f"Status: {status}")

        phases = design_module.get("phases", [])
        if phases:
            parts.append(f"Phase: {', '.join(phases)}")

        conditions = conditions_module.get("conditions", [])
        if conditions:
            parts.append(f"Conditions: {', '.join(conditions[:5])}")

        interventions = interventions_module.get("interventions", [])
        intervention_names = [i.get("name", "") for i in interventions if i.get("name")]
        if intervention_names:
            parts.append(f"Interventions: {', '.join(intervention_names[:5])}")

        lead_sponsor = sponsor_module.get("leadSponsor", {})
        sponsor_name = lead_sponsor.get("name", "")

        start_date = status_module.get("startDateStruct", {}).get("date", "")

        return RetrievedDocument(
            source_name=self.SOURCE_NAME,
            source_id=nct_id,
            title=title,
            authors=[sponsor_name] if sponsor_name else [],
            journal="ClinicalTrials.gov",
            publication_date=start_date,
            abstract="\n".join(parts),
            url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
            metadata=SourceMetadata(
                source_name=self.SOURCE_NAME,
                adapter_name="ClinicalTrialsSourceAdapter",
                query=query,
                page_size=page_size,
            ),
        )
