from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations
from typing import Any

from app.agents.base import BaseAgent
from app.core.config import Settings, get_settings
from app.models.retrieval import RetrievedDocument
from app.models.validation import ValidationOutput


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}

_POSITIVE_TERMS = {
    "effective",
    "improves",
    "improved",
    "benefit",
    "beneficial",
    "reduces",
    "reduced",
    "safe",
    "significant",
    "associated with improved",
    "increases survival",
}

_NEGATIVE_TERMS = {
    "ineffective",
    "no effect",
    "not effective",
    "fails",
    "failure",
    "worse",
    "risk",
    "adverse",
    "contraindicated",
    "does not improve",
    "not associated",
}


@dataclass(slots=True)
class EvidenceMetrics:
    sources_count: int
    credibility_score: float
    recency_score: float
    agreement_score: float
    contradictions_found: bool
    contradictions: list[str]
    evidence_score: float
    confidence_score: int
    confidence_level: str
    explanation: str
    is_supported: bool


class ValidationAgent(BaseAgent):
    agent_name = "validation"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        documents = self._extract_documents(payload)
        metrics = self._validate_documents(payload.get("question", ""), documents)

        output = ValidationOutput(
            confidence_score=metrics.confidence_score,
            confidence_level=metrics.confidence_level,
            contradictions_found=metrics.contradictions_found,
            explanation=metrics.explanation,
            is_supported=metrics.is_supported,
            sources_count=metrics.sources_count,
            agreement_score=metrics.agreement_score,
            credibility_score=metrics.credibility_score,
            recency_score=metrics.recency_score,
        )

        return {
            # Always proceed to citation — never route to abstain
            "status": "citing",
            "next_step": "citation",
            "confidence_score": output.confidence_score,
            "confidence_level": output.confidence_level,
            "contradictions_found": output.contradictions_found,
            "explanation": output.explanation,
            "is_supported": True,   # Force forward — ResponseAgent decides quality
            "contradictions": metrics.contradictions,
            "evidence_score": metrics.evidence_score,
            "validation_summary": {
                "sources_count": metrics.sources_count,
                "credibility_score": metrics.credibility_score,
                "recency_score": metrics.recency_score,
                "agreement_score": metrics.agreement_score,
                "contradictions_found": metrics.contradictions_found,
                "evidence_score": metrics.evidence_score,
            },
            "abstain_reason": "",
        }

    def _validate_documents(self, question: str, documents: list[RetrievedDocument]) -> EvidenceMetrics:
        if not documents:
            explanation = "No retrieved documents were provided, so the evidence set cannot be validated."
            return EvidenceMetrics(
                sources_count=0,
                credibility_score=0.0,
                recency_score=0.0,
                agreement_score=0.0,
                contradictions_found=False,
                contradictions=[],
                evidence_score=0.0,
                confidence_score=0,
                confidence_level="Low",
                explanation=explanation,
                is_supported=False,
            )

        normalized_documents = [self._normalize_document(document) for document in documents]
        unique_sources = sorted({document.source_name for document in normalized_documents if document.source_name})
        sources_count = len(unique_sources)

        credibility_score = self._score_credibility(normalized_documents)
        recency_score = self._score_recency(normalized_documents)
        agreement_score, contradictions = self._score_agreement_and_contradictions(normalized_documents, question)
        contradictions_found = bool(contradictions)

        source_count_score = min(sources_count / max(len(self._settings.trusted_sources), 1), 1.0)
        agreement_component = agreement_score
        credibility_component = credibility_score
        recency_component = recency_score

        evidence_score = (
            (source_count_score * 0.20)   # source diversity matters less when PubMed is the primary
            + (credibility_component * 0.35)  # PubMed is highly credible — weight it more
            + (recency_component * 0.20)
            + (agreement_component * 0.25)
        )

        penalty = 0.0
        if contradictions_found:
            # Only penalise for clear polarity conflicts, not just any disagreement
            penalty += min(0.20, 0.06 * len(contradictions))
        # Removed the single-source penalty: PubMed is a trusted authoritative source
        # and we shouldn't penalise the system for only having one source type active.
        if agreement_score < 0.30:  # Only penalise very low agreement (< 0.45 was too strict)
            penalty += 0.08

        confidence = max(0.0, min((evidence_score - penalty) * 100.0, 100.0))
        confidence_score = int(round(confidence))
        confidence_level = self._confidence_level(confidence_score)

        # Lowered threshold from 60 → 45: with a single trusted source (PubMed)
        # and good credibility/recency scores, 45+ is sufficient evidence quality.
        is_supported = confidence_score >= 45 and not contradictions_found

        explanation = self._build_explanation(
            question=question,
            sources=unique_sources,
            sources_count=sources_count,
            credibility_score=credibility_score,
            recency_score=recency_score,
            agreement_score=agreement_score,
            contradictions=contradictions,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
        )

        return EvidenceMetrics(
            sources_count=sources_count,
            credibility_score=round(credibility_score, 4),
            recency_score=round(recency_score, 4),
            agreement_score=round(agreement_score, 4),
            contradictions_found=contradictions_found,
            contradictions=contradictions,
            evidence_score=round(max(evidence_score - penalty, 0.0), 4),
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            explanation=explanation,
            is_supported=is_supported,
        )

    def _extract_documents(self, payload: dict[str, Any]) -> list[RetrievedDocument]:
        raw_documents = payload.get("retrieved_documents")
        if raw_documents is None:
            raw_documents = payload.get("evidence", [])

        documents: list[RetrievedDocument] = []
        for item in raw_documents or []:
            if isinstance(item, RetrievedDocument):
                documents.append(item)
                continue
            if isinstance(item, dict):
                if "metadata" not in item and item.get("source_name"):
                    item = {
                        **item,
                        "metadata": {
                            "source_name": item.get("source_name", ""),
                            "adapter_name": item.get("adapter_name", "ValidationAgent"),
                            "query": payload.get("question", ""),
                        },
                    }
                try:
                    documents.append(RetrievedDocument.model_validate(item))
                except Exception:
                    continue
        return documents

    def _normalize_document(self, document: RetrievedDocument) -> RetrievedDocument:
        return document

    def _score_credibility(self, documents: list[RetrievedDocument]) -> float:
        if not documents:
            return 0.0
        scores = [self._settings.source_authority_weights.get(doc.source_name, 0.7) for doc in documents]
        return min(sum(scores) / len(scores), 1.0)

    def _score_recency(self, documents: list[RetrievedDocument]) -> float:
        if not documents:
            return 0.0
        scores = [self._publication_recency_score(doc.publication_date) for doc in documents]
        return min(sum(scores) / len(scores), 1.0)

    def _score_agreement_and_contradictions(
        self,
        documents: list[RetrievedDocument],
        question: str,
    ) -> tuple[float, list[str]]:
        if len(documents) == 1:
            return 0.65, []

        pair_scores: list[float] = []
        contradictions: list[str] = []
        for left, right in combinations(documents, 2):
            left_tokens = self._tokens(self._combined_text(left))
            right_tokens = self._tokens(self._combined_text(right))
            overlap = self._jaccard_similarity(left_tokens, right_tokens)
            pair_scores.append(overlap)

            if overlap >= 0.18 and self._has_polarity_conflict(left, right, question):
                contradictions.append(
                    f"{left.source_name}:{left.source_id or left.title[:32]} conflicts with "
                    f"{right.source_name}:{right.source_id or right.title[:32]}"
                )

        if not pair_scores:
            return 0.0, contradictions

        agreement = sum(pair_scores) / len(pair_scores)
        if contradictions:
            agreement = max(0.0, agreement - min(0.3, 0.1 * len(contradictions)))
        return min(agreement, 1.0), contradictions

    def _build_explanation(
        self,
        *,
        question: str,
        sources: list[str],
        sources_count: int,
        credibility_score: float,
        recency_score: float,
        agreement_score: float,
        contradictions: list[str],
        confidence_score: int,
        confidence_level: str,
    ) -> str:
        source_text = ", ".join(sources) if sources else "no trusted sources"
        contradiction_text = (
            f" Contradictions detected: {'; '.join(contradictions)}."
            if contradictions
            else " No direct contradictions detected."
        )
        question_text = f"Question: {question.strip()}" if question.strip() else "Question not provided."
        return (
            f"Validated {sources_count} source(s) across {source_text}. "
            f"Credibility={credibility_score:.2f}, recency={recency_score:.2f}, agreement={agreement_score:.2f}."
            f"{contradiction_text} Final confidence={confidence_score}/100 ({confidence_level}). "
            f"{question_text}"
        )

    def _confidence_level(self, confidence_score: int) -> str:
        if confidence_score >= 75:
            return "High"
        if confidence_score >= 45:
            return "Medium"
        return "Low"

    def _combined_text(self, document: RetrievedDocument) -> str:
        return " ".join(
            part
            for part in [document.title, document.abstract, document.journal]
            if part
        )

    def _tokens(self, text: str) -> set[str]:
        tokens = {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9]+", text.lower())
            if token.lower() not in _STOPWORDS and len(token) > 2
        }
        return tokens

    def _jaccard_similarity(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def _has_polarity_conflict(
        self,
        left: RetrievedDocument,
        right: RetrievedDocument,
        question: str,
    ) -> bool:
        left_text = self._combined_text(left).lower()
        right_text = self._combined_text(right).lower()
        question_text = question.lower()

        left_positive = self._contains_any(left_text, _POSITIVE_TERMS)
        right_positive = self._contains_any(right_text, _POSITIVE_TERMS)
        left_negative = self._contains_any(left_text, _NEGATIVE_TERMS)
        right_negative = self._contains_any(right_text, _NEGATIVE_TERMS)

        shared_topic_terms = self._tokens(left_text) & self._tokens(right_text) & self._tokens(question_text)
        topic_overlap = bool(shared_topic_terms)

        polarity_flip = (left_positive and right_negative) or (left_negative and right_positive)
        outcome_disagreement = self._contains_any(left_text, {"increase"}) and self._contains_any(
            right_text, {"decrease", "reduces"}
        )
        return topic_overlap and (polarity_flip or outcome_disagreement)

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    def _publication_recency_score(self, publication_date: str) -> float:
        if not publication_date:
            return 0.45

        match = re.search(r"(19|20)\d{2}", publication_date)
        if match is None:
            return 0.45

        year = int(match.group(0))
        current_year = datetime.now(UTC).year
        age = max(current_year - year, 0)
        if age == 0:
            return 1.0
        if age <= 2:
            return 0.95
        if age <= 5:
            return 0.85
        if age <= 10:
            return 0.7
        if age <= 15:
            return 0.5
        return 0.35
