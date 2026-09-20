"""Metrics controller: returns live 5-Plane telemetry."""

from fastapi import APIRouter, Request

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state
from retail_intel.metrics.engine import Comprehensive5PlaneMetrics

logger = get_logger("api.routes.metrics")
router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("", response_model=Comprehensive5PlaneMetrics)
async def get_metrics(request: Request):
    """Returns real-time aggregated metrics across Business, Agentic, RAG, ML, and System planes."""
    state = get_app_state(request)
    drift_rep = state.drift_radar.run_comprehensive_audit([
        c.get("final_effective_price", 100.0) for c in state.competitor_raw_list
    ])
    return state.metrics_engine.compute_metrics(
        psi_score=drift_rep.psi_score,
        wasserstein_dist=drift_rep.wasserstein_embedding_distance,
        active_catalog_size=len(state.competitor_raw_list),
        mapped_count=len(state.competitor_raw_list) - 1,
    )
