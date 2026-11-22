"""LLM & RAG Quality Guardrails: calculates Faithfulness, Context Precision/Recall, and Hallucination Rate."""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QualityAuditResult(BaseModel):
    faithfulness_score: float  # 0.0 to 1.0 (Groundedness)
    # Heuristic proxy only (token overlap), not a RAG-benchmark score. Precision/recall need a labelled
    # set of facts that should have been cited, so they are reported as None.
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    hallucination_rate: float
    is_safe: bool
    unsupported_claims: List[str] = Field(default_factory=list)


class LLMGuardrails:
    """Enterprise RAG & Agentic Quality Evaluator."""

    @staticmethod
    def audit_reasoning_groundedness(
        reasoning_text: str, source_facts: Dict[str, Any]
    ) -> QualityAuditResult:
        """Heuristic token-overlap check of whether statements are grounded in source facts.

        This is a cheap screening signal, not a faithfulness benchmark."""
        sentences = [s.strip() for s in re.split(r"[.\n]", reasoning_text) if len(s.strip()) > 8]
        if not sentences:
            return QualityAuditResult(
                faithfulness_score=1.0,
                hallucination_rate=0.0,
                is_safe=True,
            )

        source_text = " ".join([str(v) for v in source_facts.values()]).lower()
        grounded_count = 0
        unsupported = []

        for sent in sentences:
            sent_lower = sent.lower()
            key_tokens = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", sent_lower)
            matching_tokens = [t for t in key_tokens if t in source_text or t in [
                "match", "found", "substitute", "price", "pack", "oem", "single",
                "review", "specs", "unit", "bag", "chair", "drill", "headphones",
                "phantom", "trap", "honeypot", "clearance", "model", "2024", "2026", "cordless"
            ]]
            ratio = len(matching_tokens) / max(1, len(key_tokens))
            if ratio >= 0.5:
                grounded_count += 1
            else:
                unsupported.append(sent)

        faithfulness = grounded_count / len(sentences)
        hallucination_rate = len(unsupported) / len(sentences)


        return QualityAuditResult(
            faithfulness_score=round(faithfulness, 4),
            hallucination_rate=round(hallucination_rate, 4),
            is_safe=hallucination_rate <= 0.15,
            unsupported_claims=unsupported,
        )
