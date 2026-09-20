"""Edge Case Matrix Tests: Section 10 Operational Edge Cases and Resilience Strategies."""

import pytest
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizationPipeline
from retail_intel.datascience.tier1_rules.deterministic_engine import DeterministicRuleEngine
from retail_intel.agents.supervisor import SupervisorAgent


@pytest.mark.edge_case
def test_edge_case_honeypot_trap(sample_competitor_items):
    normalizer = NormalizationPipeline()
    rule_engine = DeterministicRuleEngine([])
    item = next(c for c in sample_competitor_items if c["competitor_sku"] == "ZEN-HONEYPOT-99")
    comp_rec = normalizer.normalize_competitor_payload(item)

    res = rule_engine.evaluate(comp_rec)
    assert res.is_resolved is True
    assert res.verdict == "HONEYPOT_TRAP"


@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_edge_case_deceptive_multipack(sample_competitor_items, sample_internal_items):
    normalizer = NormalizationPipeline()
    comp_item = next(c for c in sample_competitor_items if c["competitor_sku"] == "APX-COF-3PK-AMBIG")
    int_item = next(i for i in sample_internal_items if i["sku"] == "INT-GROC-101")

    comp_rec = normalizer.normalize_competitor_payload(comp_item)
    int_rec = normalizer.normalize_internal_product(int_item)

    supervisor = SupervisorAgent()
    intel = await supervisor.execute_reasoning_flow(comp_rec, int_rec, initial_tau=0.75)

    assert intel.verdict == "EXACT_MATCH"
    assert intel.normalized_unit_price == 15.99
    assert intel.resolution.normalized_pack_size == 1
    assert intel.resolution.reflection_applied is True
    assert "single" in intel.resolution.reasoning.lower() or "single" in intel.reasoning_summary.lower()


@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_edge_case_private_label_oem(sample_competitor_items, sample_internal_items):
    normalizer = NormalizationPipeline()
    comp_item = next(c for c in sample_competitor_items if c["competitor_sku"] == "NOV-CHAIR-ERGOPRO")
    int_item = next(i for i in sample_internal_items if i["sku"] == "INT-HOME-201")

    comp_rec = normalizer.normalize_competitor_payload(comp_item)
    int_rec = normalizer.normalize_internal_product(int_item)

    supervisor = SupervisorAgent()
    intel = await supervisor.execute_reasoning_flow(comp_rec, int_rec, initial_tau=0.82)

    assert intel.verdict == "EQUIVALENT_PRIVATE_LABEL"
    assert intel.confidence >= 0.90
    assert "Knowledge Graph" in intel.resolution.reasoning or "OEM" in intel.resolution.reasoning


@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_edge_case_phantom_stock(sample_competitor_items, sample_internal_items):
    normalizer = NormalizationPipeline()
    comp_item = next(c for c in sample_competitor_items if c["competitor_sku"] == "TTN-DRILL-PHANTOM")
    int_item = next(i for i in sample_internal_items if i["sku"] == "INT-HOME-202")

    comp_rec = normalizer.normalize_competitor_payload(comp_item)
    int_rec = normalizer.normalize_internal_product(int_item)

    supervisor = SupervisorAgent()
    intel = await supervisor.execute_reasoning_flow(comp_rec, int_rec, initial_tau=0.80)

    assert intel.verdict == "UNFULFILLED_PHANTOM"
    assert intel.strategy.recommended_action == "ISOLATE_PHANTOM"
    assert intel.strategy.gross_margin_protected_usd > 0.0


@pytest.mark.edge_case
@pytest.mark.asyncio
async def test_edge_case_multimodal_information_clash(sample_competitor_items, sample_internal_items):
    normalizer = NormalizationPipeline()
    comp_item = next(c for c in sample_competitor_items if c["competitor_sku"] == "APX-CLASH-NORDIC")
    int_item = next(i for i in sample_internal_items if i["sku"] == "INT-APP-302")

    comp_rec = normalizer.normalize_competitor_payload(comp_item)
    int_rec = normalizer.normalize_internal_product(int_item)

    supervisor = SupervisorAgent()
    intel = await supervisor.execute_reasoning_flow(comp_rec, int_rec, initial_tau=0.85)

    assert intel.verdict == "CONTRADICTORY_LISTING"
    assert intel.resolution.reflection_applied is True
    assert "2024" in intel.resolution.reasoning
