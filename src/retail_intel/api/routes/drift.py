"""Drift Radar controller: statistical PSI, Wasserstein distance, and Page-Hinkley test."""

from fastapi import APIRouter, Request

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state
from retail_intel.mlops.drift_radar import DriftReport

logger = get_logger("api.routes.drift")
router = APIRouter(prefix="/api/v1/drift", tags=["drift"])


@router.get("", response_model=DriftReport)
async def get_drift_status(request: Request):
    """Returns current statistical drift report across price distribution, embeddings, and concepts."""
    state = get_app_state(request)
    prices = [c.get("final_effective_price", 100.0) for c in state.competitor_raw_list]
    return state.drift_radar.run_comprehensive_audit(current_prices=prices)
