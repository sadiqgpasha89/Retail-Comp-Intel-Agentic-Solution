"""Unit tests for 5-Plane Metrics Engine."""

import pytest
from retail_intel.metrics.engine import MetricsEngine, Comprehensive5PlaneMetrics


@pytest.mark.unit
def test_metrics_engine_computation():
    engine = MetricsEngine()
    engine.record_analysis(
        verdict="EXACT_MATCH",
        was_agentic=True,
        was_hitl_escalated=False,
        plan_optimality=0.8,
        gross_margin_protected=500.0,
        reflection_applied=True,
        tool_success=4,
        tool_errors=0,
    )

    metrics: Comprehensive5PlaneMetrics = engine.compute_metrics(
        psi_score=0.035,
        wasserstein_dist=0.025,
        active_catalog_size=10,
        mapped_count=9,
    )

    # Verify all 5 planes populated correctly
    assert metrics.business.gross_margin_protected_usd >= 500.0
    assert metrics.business.exact_match_rate == 1.0
    assert metrics.agentic.plan_optimality_ratio_avg > 0.5
    assert metrics.agentic.total_agentic_escalations == 1
    assert metrics.ml_system.bi_encoder_recall_at_5 >= 0.90
    assert metrics.ml_system.psi_distribution_score == pytest.approx(0.035, rel=1e-3)
    assert metrics.infrastructure.active_catalog_size == 10
