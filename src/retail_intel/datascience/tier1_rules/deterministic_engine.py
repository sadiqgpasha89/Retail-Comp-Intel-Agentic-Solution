"""Tier 1 Deterministic Rule Engine: Exact GTIN resolution, brand boundary gates, and honeypot isolation."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from retail_intel.core.logging import get_logger
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("datascience.tier1_rules")


class RuleResolution(BaseModel):
    is_resolved: bool
    verdict: Optional[str] = None  # "EXACT_MATCH", "HONEYPOT_TRAP", "BOUNDARY_REJECT"
    internal_sku: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""


class DeterministicRuleEngine:
    """Evaluates strict deterministic heuristics prior to vector retrieval or agentic intervention."""

    def __init__(self, internal_catalog: Optional[List[NormalizedProductRecord]] = None):
        self.gtin_index: Dict[str, NormalizedProductRecord] = {}
        if internal_catalog:
            self.build_gtin_index(internal_catalog)

    def build_gtin_index(self, records: List[NormalizedProductRecord]) -> None:
        """Indexes internal products by normalized GTIN."""
        self.gtin_index.clear()
        for rec in records:
            if rec.gtin_normalized and rec.gtin_valid:
                self.gtin_index[rec.gtin_normalized] = rec
        logger.info("Deterministic GTIN index built", indexed_gtins=len(self.gtin_index))

    def evaluate(self, competitor_record: NormalizedProductRecord) -> RuleResolution:
        """Evaluates deterministic gates."""
        raw_ref = competitor_record.raw_payload_ref or {}

        # 1. Honeypot check
        if raw_ref.get("is_honeypot") or "honeypot" in competitor_record.title_clean.lower():
            return RuleResolution(
                is_resolved=True,
                verdict="HONEYPOT_TRAP",
                confidence=1.0,
                reason="Flagged by deterministic honeypot link and payload signature filter.",
            )

        # 2. Exact GTIN/Barcode match
        if competitor_record.gtin_normalized and competitor_record.gtin_valid:
            matched_internal = self.gtin_index.get(competitor_record.gtin_normalized)
            if matched_internal:
                title_lower = competitor_record.title_clean.lower()
                if "pack" in title_lower and matched_internal.pack_size == 1:
                    # Deceptive pack size claim — escalate to agentic tier
                    return RuleResolution(
                        is_resolved=False,
                        reason="GTIN matches, but title claims multipack variance; requires agentic inspection.",
                    )

                return RuleResolution(
                    is_resolved=True,
                    verdict="EXACT_MATCH",
                    internal_sku=matched_internal.sku,
                    confidence=0.99,
                    reason=f"Exact GTIN check digit match: {competitor_record.gtin_normalized}",
                )

        return RuleResolution(
            is_resolved=False,
            reason="No exact GTIN match; passing to Tier 2 Classical ML vector retrieval.",
        )
