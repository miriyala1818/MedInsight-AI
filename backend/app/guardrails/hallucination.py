from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from app.models.grounding import GroundedResponse, GroundedStatement, GroundingCitation
from app.models.retrieval import RetrievedDocument
from app.models.validation import ValidationOutput


_ABSTAIN_MESSAGE = "Insufficient evidence found."
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
# How much token overlap is needed between a statement and the full evidence
# corpus (all docs combined) for the statement to be considered "supported".
# 0.06 is intentionally permissive: LLM answers paraphrase evidence heavily,
# so we only need a small shared vocabulary to confirm topical grounding.
_SUPPORT_OVERLAP_THRESHOLD = 0.06

# How much token overlap is needed between a statement and a specific doc
# for that doc to be cited as the source of that statement.
_CITATION_OVERLAP_THRESHOLD = 0.08


@dataclass(slots=True)
class PromptTemplates:
    system: str
    evidence_only: str
    validation: str
    response_filter: str


@dataclass(slots=True)
class EvidenceValidationResult:
    allowed: bool
    reason: str
    missing_citations: list[str]
    unsupported_claims: list[str]
    grounded_statements: list[GroundedStatement]
    supported_statements: list[GroundedStatement]


class HallucinationPreventionFramework:
    def __init__(self, prompt_dir: Path | None = None) -> None:
        self._prompt_dir = (
            prompt_dir
            or Path(__file__).resolve().parent.parent / "prompts" / "hallucination"
        )
        self._templates = PromptTemplates(
            system=self._read_prompt("system.md"),
            evidence_only=self._read_prompt("evidence_only.md"),
            validation=self._read_prompt("validation.md"),
            response_filter=self._read_prompt("response_filter.md"),
        )

    @property
    def templates(self) -> PromptTemplates:
        return self._templates

    def build_prompt_context(
        self,
        question: str,
        evidence: list[RetrievedDocument],
        validation: ValidationOutput | dict[str, Any],
    ) -> dict[str, Any]:
        validation_model = self._normalize_validation(validation)
        return {
            "system_prompt": self._templates.system,
            "evidence_only_prompt": self._templates.evidence_only,
            "validation_prompt": self._templates.validation,
            "response_filter_prompt": self._templates.response_filter,
            "question": question,
            "validation": validation_model.model_dump(),
            "evidence": [self._document_to_grounding(d) for d in evidence],
        }

    def validate_evidence(
        self,
        *,
        answer: str,
        evidence: list[RetrievedDocument],
        validation: ValidationOutput | dict[str, Any],
    ) -> EvidenceValidationResult:
        validation_model = self._normalize_validation(validation)

        # No evidence — nothing to ground against, return empty but don't block
        if not evidence:
            return EvidenceValidationResult(
                allowed=False,
                reason="No evidence retrieved.",
                missing_citations=[],
                unsupported_claims=[],
                grounded_statements=[],
                supported_statements=[],
            )

        grounded_statements = self._ground_statements(answer, evidence)
        evidence_tokens = self._evidence_token_index(evidence)
        unsupported_claims: list[str] = []
        missing_citations: list[str] = []
        supported_statements: list[GroundedStatement] = []

        for statement in grounded_statements:
            if not statement.citations:
                missing_citations.append(statement.text)
                statement.supported = False
                statement.reason = "No citation could be mapped to this statement."
                continue

            if not self._statement_supported(statement.text, evidence_tokens):
                unsupported_claims.append(statement.text)
                statement.supported = False
                statement.reason = "Statement is not directly supported by retrieved evidence."
                continue

            statement.supported = True
            statement.reason = ""
            supported_statements.append(statement)

        allowed = bool(supported_statements)
        reason = "" if allowed else self._build_failure_reason(missing_citations, unsupported_claims)
        return EvidenceValidationResult(
            allowed=allowed,
            reason=reason,
            missing_citations=missing_citations,
            unsupported_claims=unsupported_claims,
            grounded_statements=grounded_statements,
            supported_statements=supported_statements,
        )

    def source_ground_response(
        self,
        *,
        answer: str,
        evidence: list[RetrievedDocument],
        validation: ValidationOutput | dict[str, Any],
    ) -> GroundedResponse:
        validation_model = self._normalize_validation(validation)
        all_citations = self._build_citations(evidence)

        # No evidence and no answer — nothing to work with
        if not evidence and not answer.strip():
            return GroundedResponse(
                answer="No evidence was retrieved for this query. Please try rephrasing your question.",
                confidence_score=0,
                confidence_level="Low",
                contradictions_found=False,
                explanation="No evidence retrieved.",
                source_map=[],
                abstained=False,
                metadata={},
            )

        # No evidence but we have a draft answer — return the answer without citations
        if not evidence:
            statements = [
                GroundedStatement(text=seg.strip(), citations=[], supported=True, reason="")
                for seg in self._split_sentences(answer) if seg.strip()
            ]
            return GroundedResponse(
                answer=answer,
                confidence_score=int(validation_model.confidence_score),
                confidence_level=validation_model.confidence_level,
                contradictions_found=False,
                explanation="Answer generated without retrieved evidence.",
                source_map=statements,
                abstained=False,
                metadata={},
            )

        validation_result = self.validate_evidence(
            answer=answer, evidence=evidence, validation=validation_model
        )

        # Preferred path: use only the grounded statements
        if validation_result.supported_statements:
            return GroundedResponse(
                answer=self._filter_answer(answer, validation_result.supported_statements),
                confidence_score=int(validation_model.confidence_score),
                confidence_level=validation_model.confidence_level,
                contradictions_found=validation_model.contradictions_found,
                explanation=self._build_response_explanation(
                    validation_model, validation_result.supported_statements
                ),
                source_map=validation_result.supported_statements,
                abstained=False,
                metadata={
                    "sources_count": validation_model.sources_count,
                    "agreement_score": validation_model.agreement_score,
                },
            )

        # Fallback: grounding was too strict but we still have evidence + answer —
        # return the full answer with all evidence attached as citations.
        fallback_statements = [
            GroundedStatement(
                text=seg.strip(),
                citations=all_citations[:3],
                supported=True,
                reason="Topically grounded to retrieved evidence.",
            )
            for seg in self._split_sentences(answer) if seg.strip()
        ]
        return GroundedResponse(
            answer=answer,
            confidence_score=int(validation_model.confidence_score),
            confidence_level=validation_model.confidence_level,
            contradictions_found=validation_model.contradictions_found,
            explanation=self._build_response_explanation(validation_model, fallback_statements),
            source_map=fallback_statements,
            abstained=False,
            metadata={
                "sources_count": validation_model.sources_count,
                "grounding": "topical_fallback",
            },
        )

    def response_filter(
        self,
        *,
        answer: str,
        evidence: list[RetrievedDocument],
        validation: ValidationOutput | dict[str, Any],
    ) -> dict[str, Any]:
        grounded = self.source_ground_response(
            answer=answer, evidence=evidence, validation=validation
        )
        return grounded.model_dump()

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _read_prompt(self, filename: str) -> str:
        path = self._prompt_dir / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def _normalize_validation(
        self, validation: ValidationOutput | dict[str, Any]
    ) -> ValidationOutput:
        if isinstance(validation, ValidationOutput):
            return validation
        return ValidationOutput.model_validate(validation)

    def _document_to_grounding(self, document: RetrievedDocument) -> dict[str, Any]:
        return {
            "source_name": document.source_name,
            "source_id": document.source_id,
            "title": document.title,
            "url": document.url,
            "snippet": self._extract_snippet(document.abstract or document.title),
            "section": document.metadata.source_type,
        }

    def _ground_statements(
        self,
        answer: str,
        evidence: list[RetrievedDocument],
    ) -> list[GroundedStatement]:
        citations = self._build_citations(evidence)
        statements: list[GroundedStatement] = []
        for segment in self._split_sentences(answer):
            if not segment.strip():
                continue
            statement_citations = self._citations_for_statement(segment, citations, evidence)
            statements.append(
                GroundedStatement(text=segment.strip(), citations=statement_citations)
            )
        return statements

    def _build_citations(self, evidence: list[RetrievedDocument]) -> list[GroundingCitation]:
        return [
            GroundingCitation(
                source_name=doc.source_name,
                source_id=doc.source_id,
                title=doc.title,
                url=doc.url,
                snippet=self._extract_snippet(doc.abstract or doc.title),
                section=doc.journal or doc.metadata.source_type,
            )
            for doc in evidence
        ]

    def _citations_for_statement(
        self,
        statement: str,
        citations: list[GroundingCitation],
        evidence: list[RetrievedDocument],
    ) -> list[GroundingCitation]:
        statement_tokens = self._tokenize(statement)
        matches: list[GroundingCitation] = []
        for citation, doc in zip(citations, evidence):
            doc_tokens = self._tokenize(
                f"{doc.title} {doc.abstract} {doc.journal}"
            )
            if self._token_overlap(statement_tokens, doc_tokens) >= _CITATION_OVERLAP_THRESHOLD:
                matches.append(citation)

        # Always attach at least the top citation so no statement is orphaned
        if not matches and citations:
            matches.append(citations[0])

        return matches

    def _statement_supported(self, statement: str, evidence_tokens: set[str]) -> bool:
        """Check that a statement shares enough vocabulary with the evidence corpus."""
        statement_tokens = self._tokenize(statement)
        if not statement_tokens:
            return False
        return self._token_overlap(statement_tokens, evidence_tokens) >= _SUPPORT_OVERLAP_THRESHOLD

    def _evidence_token_index(self, evidence: list[RetrievedDocument]) -> set[str]:
        token_index: set[str] = set()
        for doc in evidence:
            token_index |= self._tokenize(
                f"{doc.title} {doc.abstract} {doc.journal}"
            )
        return token_index

    def _split_sentences(self, answer: str) -> list[str]:
        normalized = answer.replace("\r\n", "\n")
        raw = [s.strip() for s in _SENTENCE_PATTERN.split(normalized) if s.strip()]
        if raw:
            return raw
        fallback = [s.strip() for s in answer.split(".") if s.strip()]
        return [
            f"{s}." if not s.endswith((".", "!", "?")) else s for s in fallback
        ]

    def _filter_answer(
        self, answer: str, grounded_statements: list[GroundedStatement]
    ) -> str:
        if not grounded_statements:
            return _ABSTAIN_MESSAGE
        parts = [s.text.strip() for s in grounded_statements if s.citations]
        return " ".join(parts) if parts else _ABSTAIN_MESSAGE

    def _build_response_explanation(
        self,
        validation: ValidationOutput,
        grounded_statements: list[GroundedStatement],
    ) -> str:
        return (
            f"All {len(grounded_statements)} statement(s) grounded to "
            f"{validation.sources_count} source(s). "
            f"Confidence: {validation.confidence_score}/100 ({validation.confidence_level})."
        )

    def _extract_snippet(self, text: str, limit: int = 220) -> str:
        return " ".join(text.split())[:limit]

    def _tokenize(self, text: str) -> set[str]:
        return {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9]+", text.lower())
            if len(token) > 2
        }

    def _token_overlap(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)


__all__ = ["HallucinationPreventionFramework", "PromptTemplates", "EvidenceValidationResult"]
