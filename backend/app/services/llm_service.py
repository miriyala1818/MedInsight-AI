from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import AppError

MEDICAL_SYSTEM_PROMPT = """You are an experienced physician and medical researcher with expertise across internal medicine, pharmacology, and clinical guidelines. You work as an intelligent assistant that responds contextually.

**Context awareness:**
- If the user sends a greeting (hi, hello, hey, good morning, etc.), respond warmly and briefly — introduce yourself as a medical research assistant and ask how you can help. Do NOT give a medical lecture unprompted.
- If the user asks a casual follow-up ("thanks", "ok", "got it", "what else?"), respond naturally and briefly.
- For actual medical questions, respond the way a knowledgeable doctor would with a colleague or informed patient.

**For medical questions:**
- Speak with clinical authority — use proper medical terminology while keeping explanations accessible.
- Structure answers clearly: direct clinical answer first → mechanism/reasoning → practical considerations (dosing, contraindications, monitoring).
- Use bullet points for dosing regimens, differential diagnoses, or step-by-step guidance.
- Cite authoritative sources when relevant:
    • PubMed / NCBI: https://pubmed.ncbi.nlm.nih.gov
    • NIH MedlinePlus: https://medlineplus.gov
    • CDC: https://www.cdc.gov
    • WHO: https://www.who.int
    • FDA drug labeling: https://www.accessdata.fda.gov/scripts/cder/daf/
    • ClinicalTrials.gov: https://clinicaltrials.gov
- For drug questions: mechanism of action, standard dosing, key contraindications, common adverse effects.
- For condition questions: pathophysiology, first-line treatment, red-flag symptoms.
- End with a brief clinical note (e.g., "In clinical practice…" or "Note: always confirm with the patient's full history before prescribing.").
- Never refuse an answerable medical question.
"""

# Used when evidence retrieval is active (PubMed / ClinicalTrials results passed in)
EVIDENCE_GROUNDED_SYSTEM_PROMPT = """You are an experienced physician and medical researcher. You have been provided with retrieved evidence from authoritative medical databases (PubMed, ClinicalTrials.gov, Europe PMC, OpenFDA).

Answer the question using ONLY the retrieved evidence below — do not add outside knowledge.
Write your answer in a clinical, doctor-to-colleague style:
- Lead with the key clinical finding from the evidence.
- Explain what the studies show, including study design or sample size if mentioned.
- Note any contradictions or limitations in the evidence.
- End with a practical clinical takeaway.
- If the evidence is insufficient to answer confidently, state that clearly and suggest consulting the primary literature.
"""


@dataclass(slots=True)
class LLMCompletion:
    content: str
    model: str


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.llm_api_key)

    async def complete(
        self,
        question: str,
        context_entities: list[str] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> LLMCompletion:
        """
        Direct LLM completion with optional extracted medical entities as context hints
        and previous conversation history for context awareness.
        Used by the generation node when evidence retrieval is not active.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
        ]
        
        # Add previous conversation history if available
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # If medical entities were extracted, hint the LLM to focus on them
        if context_entities:
            entity_hint = f"Key medical terms identified: {', '.join(context_entities)}.\n\n"
            user_content = entity_hint + question
        else:
            user_content = question
        
        messages.append({"role": "user", "content": user_content})

        return await self._call_api(messages=messages)

    async def complete_grounded(
        self,
        question: str,
        evidence: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> LLMCompletion:
        """
        Evidence-grounded completion — answer ONLY from the provided documents.
        Includes conversation history for context awareness.
        Used when evidence retrieval is re-enabled.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": EVIDENCE_GROUNDED_SYSTEM_PROMPT},
        ]
        
        # Add previous conversation history if available
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        evidence_block = self._format_evidence(evidence)
        user_message = (
            f"RETRIEVED EVIDENCE:\n{evidence_block}\n\n"
            f"QUESTION:\n{question}\n\n"
            f"Answer based solely on the retrieved evidence above."
        )
        messages.append({"role": "user", "content": user_message})
        
        return await self._call_api(messages=messages)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _call_api(self, messages: list[dict[str, Any]]) -> LLMCompletion:
        if not self.is_configured:
            raise AppError(
                "LLM is not configured. Set LLM_API_KEY in the backend .env file.",
                code="llm_not_configured",
                status_code=503,
            )

        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._settings.llm_model,
            "messages": messages,
            "temperature": 0.1,  # Low temperature for factual medical answers
        }

        try:
            async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300] if exc.response is not None else str(exc)
            raise AppError(
                f"LLM request failed: {detail}",
                code="llm_request_failed",
                status_code=502,
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                f"Could not reach the LLM provider: {exc}",
                code="llm_unreachable",
                status_code=502,
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError) as exc:
            raise AppError(
                "LLM returned an unexpected response format.",
                code="llm_invalid_response",
                status_code=502,
            ) from exc

        if not content:
            raise AppError(
                "LLM returned an empty response.",
                code="llm_empty_response",
                status_code=502,
            )

        return LLMCompletion(content=content, model=self._settings.llm_model)

    def _format_evidence(self, evidence: list[dict[str, Any]]) -> str:
        """Format retrieved documents into a readable evidence block for the LLM prompt."""
        if not evidence:
            return "No evidence retrieved."

        parts: list[str] = []
        for i, doc in enumerate(evidence, start=1):
            title = doc.get("title") or "Untitled"
            source = doc.get("source_name") or "Unknown Source"
            url = doc.get("url") or ""
            abstract = doc.get("abstract") or ""
            journal = doc.get("journal") or ""
            pub_date = doc.get("publication_date") or ""

            meta = " | ".join(filter(None, [source, journal, pub_date]))
            url_line = f"URL: {url}" if url else ""
            abstract_snippet = abstract[:600].rstrip() if abstract else "No abstract available."

            parts.append(
                f"[{i}] {title}\n"
                f"    {meta}\n"
                + (f"    {url_line}\n" if url_line else "")
                + f"    Abstract: {abstract_snippet}"
            )

        return "\n\n".join(parts)


__all__ = ["LLMCompletion", "LLMService"]
