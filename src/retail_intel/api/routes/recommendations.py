"""API Routes for Retail Merchandising Recommendations & Strategic Directives."""

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state
from retail_intel.datascience.recommendation_engine import (
    recommendation_engine,
    RecommendationsSummary,
    MerchandisingAction,
)
from retail_intel.data_engineering.dataset_generator import DatasetGenerator
from retail_intel.domain.recommendations import (
    InsufficientInputs,
    InvalidTransition,
    NotAuthorized,
    PolicyBlocked,
    RecStatus,
    RecType,
    Recommendation,
    SkuContext,
    WorkflowError,
    WritesDisabled,
    estimate_margin_impact,
)
from retail_intel.core.config import settings

logger = get_logger("api.routes.recommendations")
router = APIRouter(prefix="/api/v1/recommendations", tags=["Executive Recommendations"])


class OrchestrateRecommendationRequest(BaseModel):
    competitor_sku: Optional[str] = Field(None, description="Specific competitor SKU to arbitrate")
    force_refresh: bool = Field(default=False, description="Re-run full catalog generation")


class DecisionRequest(BaseModel):
    notes: str = ""


class RejectRequest(BaseModel):
    reason: str


class ExecuteRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=8)
    dry_run: bool = True


class OutcomeRequest(BaseModel):
    measured: Dict[str, Any]


# Demo identity. These headers identify the *claimed* actor for the audit trail. They are NOT
# authentication: real SSO/RBAC is a documented gap (docs/CAPABILITY_MATRIX.md, backlog B-01).
def _actor(actor_id: Optional[str], role: Optional[str]) -> tuple[str, str]:
    return (actor_id or "anonymous", (role or "viewer").lower())


_ACTION_TO_TYPE = {
    "AUTO_REPRICE_VOLUME_DEFENSE": RecType.REVIEW_PRICE,
    "HOLD_MARGIN_PHANTOM_DEFENSE": RecType.HOLD_PRICE,
    "ENFORCE_MAP_POLICY": RecType.ESCALATE_COMPLIANCE,
    "OEM_PRIVATE_LABEL_ARBITRAGE": RecType.SOURCE_EQUIVALENT,
    "BASKET_BUILDER_BUNDLE": RecType.EVALUATE_PROMOTION,
}
_PRICE_TYPES = {RecType.REVIEW_PRICE, RecType.HOLD_PRICE, RecType.EVALUATE_PROMOTION}


def _stable_id(a: MerchandisingAction) -> str:
    key = f"{a.action_type}|{a.internal_sku}|{a.competitor_sku}"
    return "rec_" + hashlib.sha256(key.encode()).hexdigest()[:16]


def _register(state, actions: List[MerchandisingAction]) -> None:
    """Idempotently turn engine output into governed Recommendations (status PROPOSED)."""
    for a in actions:
        a.workflow_id = _stable_id(a)
        rec_type = _ACTION_TO_TYPE.get(a.action_type, RecType.INVESTIGATE)
        price_action = rec_type in _PRICE_TYPES
        cur = Decimal(str(a.internal_price))
        prop = Decimal(str(a.recommended_price)) if price_action else None
        estimate = estimate_margin_impact(
            current_price=cur, proposed_price=prop, unit_cost=Decimal(str(a.cogs)),
            weekly_units=None, elasticity_low=None, elasticity_expected=None, elasticity_high=None,
        ) if price_action else None
        state.workflow.propose(Recommendation(
            recommendation_id=a.workflow_id,
            tenant_id=settings.tenant_id,
            rec_type=rec_type,
            internal_sku=a.internal_sku,
            competitor_listing_id=a.competitor_sku,
            currency="USD",
            current_price=cur,
            proposed_price=prop,
            rationale=a.strategic_rationale,
            assumptions=[
                "Demo/synthetic catalog data; currency assumed USD (catalog carries no currency field).",
                "Engine rationale is a hypothesis, not a verified competitor intent.",
            ],
            estimate=estimate if not isinstance(estimate, InsufficientInputs) else None,
            estimate_gap=estimate if isinstance(estimate, InsufficientInputs) else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ), actor="recommendation_engine")


def _context_for(state, rec: Recommendation) -> SkuContext:
    raw = next((i for i in state.internal_raw_list if i.get("sku") == rec.internal_sku), None)
    if raw is None:
        raise HTTPException(status_code=409, detail=f"Internal SKU {rec.internal_sku} is not in the active catalog")
    cogs = raw.get("cost_of_goods")
    inv = raw.get("inventory_units")
    return SkuContext(
        internal_sku=rec.internal_sku,
        price=Decimal(str(raw["current_price"])),
        currency="USD",
        cogs=Decimal(str(cogs)) if cogs is not None else None,
        inventory_units=int(inv) if inv is not None else None,
        map_price=Decimal(str(raw["map_price"])) if raw.get("map_price") is not None else None,
    )


def _http(exc: WorkflowError) -> HTTPException:
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, PolicyBlocked):
        return HTTPException(status_code=422, detail={
            "error": "POLICY_BLOCKED",
            "violations": [v.model_dump() for v in exc.violations],
        })
    if isinstance(exc, WritesDisabled):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, InvalidTransition):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=404 if str(exc).startswith("Unknown") else 400, detail=str(exc))


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
    _register(state, summary.top_actions)

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


@router.get("/workflow")
async def list_workflow(request: Request, status: Optional[RecStatus] = None):
    """Governed recommendations and their lifecycle state (PROPOSED -> ... -> MEASURED)."""
    state = get_app_state(request)
    return [r.model_dump(mode="json") for r in state.workflow.list(status)]


@router.get("/workflow/{rec_id}")
async def get_workflow_item(rec_id: str, request: Request):
    state = get_app_state(request)
    try:
        return state.workflow.get(rec_id).model_dump(mode="json")
    except WorkflowError as e:
        raise _http(e)


@router.post("/{rec_id}/review")
async def review_recommendation(rec_id: str, body: DecisionRequest, request: Request,
                                x_actor_id: Optional[str] = Header(None), x_actor_role: Optional[str] = Header(None)):
    state = get_app_state(request)
    actor, role = _actor(x_actor_id, x_actor_role)
    try:
        return state.workflow.review(rec_id, actor, role, body.notes).model_dump(mode="json")
    except WorkflowError as e:
        raise _http(e)


@router.post("/{rec_id}/approve")
async def approve_recommendation(rec_id: str, body: DecisionRequest, request: Request,
                                 x_actor_id: Optional[str] = Header(None), x_actor_role: Optional[str] = Header(None)):
    """Approval is a *decision record only*: it runs the policy checks (margin floor, MAP, bounds, ...) and
    never changes a price anywhere. Execution is a separate, dry-run-by-default step."""
    state = get_app_state(request)
    actor, role = _actor(x_actor_id, x_actor_role)
    try:
        rec = state.workflow.get(rec_id)
        return state.workflow.approve(rec_id, actor, role, _context_for(state, rec), body.notes).model_dump(mode="json")
    except WorkflowError as e:
        raise _http(e)


@router.post("/{rec_id}/reject")
async def reject_recommendation(rec_id: str, body: RejectRequest, request: Request,
                                x_actor_id: Optional[str] = Header(None), x_actor_role: Optional[str] = Header(None)):
    state = get_app_state(request)
    actor, role = _actor(x_actor_id, x_actor_role)
    try:
        return state.workflow.reject(rec_id, actor, role, body.reason).model_dump(mode="json")
    except WorkflowError as e:
        raise _http(e)


@router.post("/{rec_id}/execute")
async def execute_recommendation(rec_id: str, body: ExecuteRequest, request: Request,
                                 x_actor_id: Optional[str] = Header(None), x_actor_role: Optional[str] = Header(None)):
    """Dry-run by default and idempotent per key. A real write needs WRITES_ENABLED=true *and* a configured
    write integration; neither ships with this repo, so `dry_run=false` is refused (409)."""
    state = get_app_state(request)
    actor, _ = _actor(x_actor_id, x_actor_role)
    try:
        return state.workflow.execute(rec_id, actor, body.idempotency_key, dry_run=body.dry_run)
    except WorkflowError as e:
        raise _http(e)


@router.post("/{rec_id}/outcome")
async def record_outcome(rec_id: str, body: OutcomeRequest, request: Request,
                         x_actor_id: Optional[str] = Header(None)):
    state = get_app_state(request)
    try:
        return state.workflow.record_outcome(rec_id, x_actor_id or "anonymous", body.measured).model_dump(mode="json")
    except WorkflowError as e:
        raise _http(e)
