"""Integration tests for end-to-end data pipeline: Ingest -> Normalize -> Vector Search -> Tri-Tier Split."""

import pytest
from retail_intel.data_engineering.ingestion.ingestion_pipeline import IngestionPipeline
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizationPipeline
from retail_intel.data_engineering.feature_store.feature_store import FeatureStore
from retail_intel.datascience.tier1_rules.deterministic_engine import DeterministicRuleEngine
from retail_intel.datascience.tier2_ml.bi_encoder import BiEncoderCandidateRetriever
from retail_intel.datascience.tier2_ml.cross_encoder import CrossEncoderScorer, DecisionSplit
from retail_intel.agents.supervisor import SupervisorAgent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_pipeline_execution(sample_internal_items, sample_competitor_items):
    # 1. Normalization
    normalizer = NormalizationPipeline()
    internal_records = [normalizer.normalize_internal_product(x) for x in sample_internal_items]

    # 2. Vector indexing
    feature_store = FeatureStore()
    feature_store.index_internal_catalog(internal_records)

    # 3. Rule engine
    rule_engine = DeterministicRuleEngine(internal_records)
    bi_encoder = BiEncoderCandidateRetriever(feature_store)
    cross_encoder = CrossEncoderScorer()
    supervisor = SupervisorAgent()

    # Process competitor item: Zenith OLED TV (ambiguous borderline match with checkout discount)
    zenith_item = next(c for c in sample_competitor_items if c["competitor_sku"] == "ZEN-TV-65-OLED")
    comp_rec = normalizer.normalize_competitor_payload(zenith_item)

    # Check Tier 1
    rule_res = rule_engine.evaluate(comp_rec)
    assert rule_res.is_resolved is False  # No exact GTIN

    # Check Tier 2
    candidates = bi_encoder.retrieve_candidates(comp_rec, top_k=1)
    assert len(candidates) == 1
    best_sku, sim, best_internal = candidates[0]
    assert best_sku == "INT-EL-002"  # VortexView 65 OLED

    pair_score = cross_encoder.score_pair(comp_rec, best_internal, sim)
    assert pair_score.decision in [DecisionSplit.AGENTIC_ESCALATION, DecisionSplit.AUTO_COMMIT]

    # Check Tier 3 Multi-Agent
    intelligence = await supervisor.execute_reasoning_flow(
        comp_rec, best_internal, pair_score.score, internal_cogs=1100.0
    )
    assert intelligence.verdict in ["DIRECT_SUBSTITUTE", "EQUIVALENT_PRIVATE_LABEL"]
    assert intelligence.effective_competitor_price == 1599.00
    assert intelligence.promotions.cart_discount == 50.00
    assert intelligence.promotions.coupon_clipped == 150.00
    assert len(intelligence.execution_trace) >= 5
