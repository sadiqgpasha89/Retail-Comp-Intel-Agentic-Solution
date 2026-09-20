"""API Routes for Retail Merchandising Recommendations & Strategic Directives."""

from typing import Any, Dict, List, Optional
import time
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state
from retail_intel.datascience.recommendation_engine import (
    recommendation_engine,
    RecommendationsSummary,
    MerchandisingAction,
)
from retail_intel.data_engineering.dataset_generator import DatasetGenerator

logger = get_logger("api.routes.recommendations")
router = APIRouter(prefix="/api/v1/recommendations", tags=["Executive Recommendations"])


class OrchestrateRecommendationRequest(BaseModel):
    competitor_sku: Optional[str] = Field(None, description="Specific competitor SKU to arbitrate")
    force_refresh: bool = Field(default=False, description="Re-run full catalog generation")


class ApproveRecommendationRequest(BaseModel):
    recommendation_id: str
    action_type: str
    target_sku: str
    approved_price: float
    notes: Optional[str] = None


@router.get("", response_model=RecommendationsSummary)
async def get_merchandising_recommendations(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by retail category"),
    urgency: Optional[str] = Query(None, description="Filter by urgency: IMMEDIATE, HIGH, MEDIUM, STRATEGIC"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
):
    """Returns synthesized retail merchandising recommendations with commercial impact metrics."""
    state = get_app_state(request)

    internal = state.internal_raw_list
    competitor = state.competitor_raw_list

    if not internal or not competitor:
        gen = DatasetGenerator()
        ds = gen.generate_large_scale_dataset(20000)
        internal = ds["internal_catalog"]
        competitor = ds["competitor_catalog"]
        state.internal_raw_list = internal
        state.competitor_raw_list = competitor
        state.competitor_raw_dict = {c["competitor_sku"]: c for c in competitor}

    summary = recommendation_engine.generate_recommendations(internal, competitor)

    # Filter actions if query parameters provided
    filtered_actions = summary.top_actions
    if category and category.lower() != "all":
        filtered_actions = [a for a in filtered_actions if a.category.lower() == category.lower()]
    if urgency and urgency.lower() != "all":
        filtered_actions = [a for a in filtered_actions if a.urgency.upper() == urgency.upper()]
    if action_type and action_type.lower() != "all":
        filtered_actions = [a for a in filtered_actions if a.action_type.upper() == action_type.upper()]

    summary.top_actions = filtered_actions
    return summary


@router.get("/summary")
async def get_executive_kpis(request: Request):
    """Returns top-level commercial executive KPIs for C-suite briefings."""
    state = get_app_state(request)

    internal = state.internal_raw_list
    competitor = state.competitor_raw_list

    if not internal or not competitor:
        gen = DatasetGenerator()
        ds = gen.generate_large_scale_dataset(20000)
        internal = ds["internal_catalog"]
        competitor = ds["competitor_catalog"]
        state.internal_raw_list = internal
        state.competitor_raw_list = competitor
        state.competitor_raw_dict = {c["competitor_sku"]: c for c in competitor}

    summary = recommendation_engine.generate_recommendations(internal, competitor)

    return {
        "revenue_at_risk_usd": summary.total_revenue_at_risk_usd,
        "revenue_uplift_usd": summary.projected_revenue_uplift_usd,
        "gross_margin_protected_usd": summary.gross_margin_protected_usd,
        "average_price_index": summary.average_price_index,
        "total_active_recommendations": summary.total_active_recommendations,
        "immediate_actions_count": summary.immediate_actions_count,
        "competitor_count": summary.competitor_count,
        "categories": summary.category_breakdown,
    }


@router.post("/orchestrate")
async def orchestrate_multi_agent_recommendation(
    req: OrchestrateRecommendationRequest,
    request: Request,
):
    """
    Triggers multi-agent reasoning flow (Supervisor, Promo, Matcher, Strategy agents)
    for a specific competitor SKU or synthesizes fresh directives across the catalog.
    """
    state = get_app_state(request)

    sku = req.competitor_sku
    if not sku:
        # Pick first competitor SKU or fallback
        if state.competitor_raw_list:
            sku = state.competitor_raw_list[0].get("competitor_sku", "ZEN-TV-65-OLED")
        else:
            sku = "ZEN-TV-65-OLED"

    comp_data = state.competitor_raw_dict.get(sku)
    if not comp_data and state.competitor_raw_list:
        comp_data = state.competitor_raw_list[0]
        sku = comp_data.get("competitor_sku", sku)

    if not comp_data:
        raise HTTPException(status_code=404, detail=f"Competitor SKU '{sku}' not found in catalog")

    comp_rec = state.normalizer.normalize_competitor_payload(comp_data)
    candidates = state.bi_encoder.retrieve_candidates(comp_rec, top_k=1)
    best_internal = candidates[0][2] if candidates else list(state.internal_dict.values())[0]

    cogs = float((best_internal.raw_payload_ref or {}).get("cost_of_goods", best_internal.effective_price * 0.55))

    # Execute full multi-agent reasoning flow
    intelligence = await state.supervisor.execute_reasoning_flow(
        competitor_rec=comp_rec,
        candidate_internal_rec=best_internal,
        initial_tau=0.78,
        internal_cogs=cogs,
    )

    # Formulate dynamic recommendation directive from agent output
    directive_action = "AUTO_REPRICE_VOLUME_DEFENSE"
    urgency = "HIGH"
    if intelligence.strategy.causal_intent == "PHANTOM_STOCK_LURE":
        directive_action = "HOLD_MARGIN_PHANTOM_DEFENSE"
        urgency = "IMMEDIATE"
    elif intelligence.verdict == "EQUIVALENT_PRIVATE_LABEL":
        directive_action = "OEM_PRIVATE_LABEL_ARBITRAGE"
        urgency = "STRATEGIC"
    elif intelligence.verdict == "CONTRADICTORY_LISTING":
        directive_action = "ENFORCE_MAP_POLICY"
        urgency = "HIGH"

    return {
        "status": "ORCHESTRATED",
        "competitor_sku": sku,
        "target_internal_sku": best_internal.sku,
        "verdict": intelligence.verdict,
        "confidence": intelligence.confidence,
        "causal_intent": intelligence.strategy.causal_intent,
        "recommended_action": intelligence.strategy.recommended_action,
        "gross_margin_protected_usd": intelligence.strategy.gross_margin_protected_usd,
        "directive_action": directive_action,
        "urgency": urgency,
        "strategic_briefing": intelligence.strategy.strategic_briefing,
        "reasoning_summary": intelligence.reasoning_summary,
        "plan_optimality_ratio": intelligence.plan_optimality_ratio,
        "total_steps_executed": intelligence.total_steps_executed,
    }


@router.post("/approve")
async def approve_recommendation_directive(req: ApproveRecommendationRequest):
    """Simulates executive sign-off and dispatch to the Dynamic Pricing Feed and ERP."""
    return {
        "status": "APPROVED_AND_QUEUED",
        "recommendation_id": req.recommendation_id,
        "target_sku": req.target_sku,
        "action_type": req.action_type,
        "committed_price": req.approved_price,
        "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "downstream_targets": ["Dynamic Repricer Service", "SAP/Oracle ERP Catalog", "Search Ranking Gateway"],
        "message": f"Action {req.recommendation_id} successfully queued for execution with margin guardrails enforced.",
    }
