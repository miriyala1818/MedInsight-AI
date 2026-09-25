from __future__ import annotations

import re
from typing import Any

from app.agents.base import BaseAgent

# ---------------------------------------------------------------------------
# Patterns used for entity extraction (downstream use, not gating)
# ---------------------------------------------------------------------------
_DRUG_PATTERN = re.compile(
    r"\b(?:metformin|aspirin|ibuprofen|paracetamol|acetaminophen|amoxicillin|atorvastatin|"
    r"lisinopril|omeprazole|sertraline|fluoxetine|warfarin|heparin|insulin|prednisone|"
    r"dexamethasone|hydroxychloroquine|remdesivir|ivermectin|azithromycin|penicillin|"
    r"ciprofloxacin|methotrexate|rituximab|pembrolizumab|nivolumab|trastuzumab|bevacizumab|"
    r"semaglutide|ozempic|wegovy|tirzepatide|dupilumab|apixaban|rivaroxaban)\b",
    re.IGNORECASE,
)
_CONDITION_PATTERN = re.compile(
    r"\b(?:diabetes|hypertension|cancer|tumor|carcinoma|lymphoma|leukemia|asthma|copd|"
    r"covid|sars|influenza|pneumonia|sepsis|stroke|myocardial infarction|heart failure|"
    r"arrhythmia|depression|anxiety|schizophrenia|alzheimer|parkinson|epilepsy|seizure|"
    r"obesity|arthritis|lupus|multiple sclerosis|hiv|aids|hepatitis|cirrhosis|"
    r"kidney disease|renal failure|heart disease|cardiovascular|atherosclerosis|"
    r"osteoporosis|fibromyalgia|chronic pain|infection|inflammation|allergy|"
    r"autoimmune|immunodeficiency)\b",
    re.IGNORECASE,
)
_TREATMENT_PATTERN = re.compile(
    r"\b(?:treatment|therapy|clinical trial|dosage|dose|efficacy|safety|side effect|"
    r"adverse effect|mechanism|pharmacokinetics|pharmacodynamics|interaction|"
    r"contraindication|prophylaxis|diagnosis|prognosis|prevention|surgery|vaccine|"
    r"immunotherapy|chemotherapy|radiotherapy|biomarker|endpoint|randomized|"
    r"meta-analysis|systematic review|cohort|placebo|double-blind)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Clearly off-topic categories — only these get redirected.
# Anything ambiguous or short is passed to the LLM.
# ---------------------------------------------------------------------------
_OFF_TOPIC_PATTERN = re.compile(
    r"\b(?:"
    # Food / cooking
    r"recipe|cook|bake|ingredient|cuisine|restaurant|food|meal|dish|snack|dessert|"
    # Politics / news
    r"election|president|minister|parliament|politics|government|war|military|"
    # Sports
    r"football|cricket|basketball|tennis|soccer|sport|match|tournament|score|goal|"
    # Entertainment
    r"movie|film|actor|actress|celebrity|music|song|album|concert|game|gaming|"
    # Finance (non-pharma)
    r"stock|bitcoin|crypto|invest|trading|forex|economy|gdp|inflation|"
    # Weather
    r"weather|forecast|temperature|rain|snow|hurricane|climate"
    r")\b",
    re.IGNORECASE,
)

# Short messages and greetings — always pass through, let the LLM respond naturally
_SHORT_MESSAGE_MAX_WORDS = 6


class PlannerAgent(BaseAgent):
    """
    Classifies the user's intent and prepares context for the LLM.

    - Very short messages (greetings, hi, thanks) → pass through
    - Clearly off-topic (cooking, sports, politics) → politely redirect
    - Everything else → pass to LLM with extracted entities as context
    """

    agent_name = "planner"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = str(payload.get("question", "")).strip()

        if not question:
            return {
                "status": "completed",
                "next_step": "response",
                "answer": "Please type a question and I'll do my best to help.",
                "entities": [],
                "information_needs": [],
            }

        word_count = len(question.split())

        # Check for off-topic queries FIRST (before short message bypass)
        # Only reject if the message is clearly about an unrelated domain AND
        # contains no medical signals at all
        is_off_topic = bool(_OFF_TOPIC_PATTERN.search(question))
        has_medical = bool(
            _DRUG_PATTERN.search(question)
            or _CONDITION_PATTERN.search(question)
            or _TREATMENT_PATTERN.search(question)
        )

        if is_off_topic and not has_medical:
            return {
                "status": "completed",
                "next_step": "response",
                "answer": (
                    "I'm a medical research assistant — I focus on drugs, treatments, "
                    "conditions, and clinical findings. How can I help with a health or "
                    "pharmaceutical question?"
                ),
                "entities": [],
                "information_needs": [question],
            }

        # Short medical or ambiguous messages (hi, hello, thanks, how are you, etc.)
        # Skip retrieval — go straight to LLM generation
        if word_count <= _SHORT_MESSAGE_MAX_WORDS:
            return self._pass_through(question, skip_retrieval=True)

        # Everything else → extract entities and pass to the LLM with retrieval
        return self._pass_through(question, skip_retrieval=False)

    def _pass_through(self, question: str, skip_retrieval: bool = False) -> dict[str, Any]:
        drugs = list({m.group(0).lower() for m in _DRUG_PATTERN.finditer(question)})
        conditions = list({m.group(0).lower() for m in _CONDITION_PATTERN.finditer(question)})
        treatments = list({m.group(0).lower() for m in _TREATMENT_PATTERN.finditer(question)})
        entities = drugs + conditions + treatments

        # Skip retrieval for greetings / short messages — go straight to generation
        next_step = "generation" if skip_retrieval else "retrieval"

        return {
            "status": "generating" if skip_retrieval else "retrieving",
            "next_step": next_step,
            "entities": entities,
            "information_needs": [question],
        }
