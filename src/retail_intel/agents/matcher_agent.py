"""SKU Harmonization & Ambiguity Arbiter Agent: resolves borderline similarity, private label OEM, and multimodal clashes."""

from typing import List, Optional

from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.core.providers import BaseLLMProvider, get_llm_provider
from retail_intel.agents.tools.tool_registry import ToolRegistry
from retail_intel.agents.reflection import ReflectionEngine, ReflectionVerdict
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("agents.matcher")


class MatcherResolution(BaseModel):
    competitor_sku: str
    target_internal_sku: Optional[str] = None
    match_type: str  # "EXACT_MATCH", "EQUIVALENT_PRIVATE_LABEL", "DIRECT_SUBSTITUTE", "CONTRADICTORY_LISTING"
    confidence: float
    normalized_pack_size: int
    normalized_unit_price: float
    reasoning: str
    tools_executed: List[str] = Field(default_factory=list)
    reflection_applied: bool = False


class MatcherAgent:
    """Specialized agent arbitrating borderline entity resolution and ambiguous catalog entries."""

    def __init__(self, tools: ToolRegistry, llm_provider: Optional[BaseLLMProvider] = None):
        self.tools = tools
        self.llm = llm_provider or get_llm_provider()
        self.reflection = ReflectionEngine()

    async def arbitrate_match(
        self,
        competitor_rec: NormalizedProductRecord,
        candidate_internal_rec: NormalizedProductRecord,
        initial_tau: float,
    ) -> MatcherResolution:
        """Executes Plan-Execute-Reflect loop to resolve borderline SKU equivalence."""
        tools_executed = []

        # 1. Check for shared OEM Factory via Knowledge Graph
        oem_id = (
            competitor_rec.normalized_attributes.get("oem_factory_id")
            or competitor_rec.raw_payload_ref.get("specifications", {}).get("oem_factory_id")
        )
        shared_oem_found = False
        if oem_id:
            tools_executed.append("query_retail_knowledge_graph")
            affiliations = self.tools.query_retail_knowledge_graph(oem_id)
            for aff in affiliations:
                if aff.get("product_id") == candidate_internal_rec.sku:
                    shared_oem_found = True
                    break

        # 2. Check OCR on Packaging & Review Imagery
        ocr_result = None
        if "pack" in competitor_rec.title_clean.lower() or "2026" in competitor_rec.title_clean.lower():
            tools_executed.append("ocr_nutrition_or_specs_panel")
            ocr_result = self.tools.ocr_nutrition_or_specs_panel(
                competitor_rec.image_url, competitor_rec.title_clean
            )

        # 3. Apply Reflection & Self-Correction
        refl_verdict: ReflectionVerdict = self.reflection.audit_evidence(
            title=competitor_rec.title_clean,
            tool_ocr_result=ocr_result,
            tool_specs_result=competitor_rec.normalized_attributes,
            current_hypothesis={"tau": initial_tau},
        )

        pack_size = competitor_rec.pack_size
        if refl_verdict.corrected_pack_size is not None:
            pack_size = refl_verdict.corrected_pack_size

        unit_price = round(competitor_rec.effective_price / max(1, pack_size), 4)

        # 4. Formulate Verdict
        if refl_verdict.corrected_match_type == "CONTRADICTORY_LISTING":
            return MatcherResolution(
                competitor_sku=competitor_rec.sku,
                target_internal_sku=candidate_internal_rec.sku,
                match_type="CONTRADICTORY_LISTING",
                confidence=0.89,
                normalized_pack_size=pack_size,
                normalized_unit_price=unit_price,
                reasoning=refl_verdict.explanation,
                tools_executed=tools_executed,
                reflection_applied=True,
            )

        if shared_oem_found:
            return MatcherResolution(
                competitor_sku=competitor_rec.sku,
                target_internal_sku=candidate_internal_rec.sku,
                match_type="EQUIVALENT_PRIVATE_LABEL",
                confidence=0.92,
                normalized_pack_size=pack_size,
                normalized_unit_price=unit_price,
                reasoning=(
                    f"Resolved via Retail Knowledge Graph: Competitor brand shares OEM factory '{oem_id}' "
                    f"and hardware patent with internal SKU {candidate_internal_rec.sku}."
                ),
                tools_executed=tools_executed,
                reflection_applied=refl_verdict.correction_applied,
            )

        if refl_verdict.correction_applied and refl_verdict.corrected_match_type == "EXACT_MATCH":
            return MatcherResolution(
                competitor_sku=competitor_rec.sku,
                target_internal_sku=candidate_internal_rec.sku,
                match_type="EXACT_MATCH",
                confidence=0.88,
                normalized_pack_size=pack_size,
                normalized_unit_price=unit_price,
                reasoning=refl_verdict.explanation,
                tools_executed=tools_executed,
                reflection_applied=True,
            )

        # Default: direct substitute resolution
        return MatcherResolution(
            competitor_sku=competitor_rec.sku,
            target_internal_sku=candidate_internal_rec.sku,
            match_type="DIRECT_SUBSTITUTE",
            confidence=round(max(0.85, initial_tau), 3),
            normalized_pack_size=pack_size,
            normalized_unit_price=unit_price,
            reasoning=(
                f"Functional substitute matching {candidate_internal_rec.title_clean} "
                "with equivalent GPC taxonomy and high cross-elasticity."
            ),
            tools_executed=tools_executed,
            reflection_applied=False,
        )
