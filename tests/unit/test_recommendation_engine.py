"""Unit tests for the Retail Merchandising & Pricing Recommendation Engine."""

import pytest
from retail_intel.datascience.recommendation_engine import RecommendationEngine, RecommendationsSummary
from retail_intel.data_engineering.dataset_generator import DatasetGenerator


def test_recommendation_engine_generation():
    generator = DatasetGenerator(random_seed=42)
    dataset = generator.generate_large_scale_dataset(total_datapoints=20000)

    engine = RecommendationEngine()
    summary: RecommendationsSummary = engine.generate_recommendations(
        internal_catalog=dataset["internal_catalog"],
        competitor_catalog=dataset["competitor_catalog"],
        observations=dataset["observations"],
    )

    assert summary.total_active_recommendations > 0
    assert summary.competitor_count >= 20
    assert summary.gross_margin_protected_usd > 0
    assert summary.average_price_index > 0
    assert len(summary.top_actions) > 0

    first_action = summary.top_actions[0]
    assert first_action.recommendation_id.startswith("REC-")
    assert first_action.action_type in [
        "AUTO_REPRICE_VOLUME_DEFENSE",
        "HOLD_MARGIN_PHANTOM_DEFENSE",
        "ENFORCE_MAP_POLICY",
        "OEM_PRIVATE_LABEL_ARBITRAGE",
        "BASKET_BUILDER_BUNDLE",
    ]
    assert first_action.urgency in ["IMMEDIATE", "HIGH", "MEDIUM", "STRATEGIC"]
    assert len(first_action.action_steps) > 0
    assert len(first_action.guardrails) > 0
