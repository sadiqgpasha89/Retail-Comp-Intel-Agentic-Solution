"""Intelligence route: orchestrates the Tri-Tier Hybrid Intelligence Pipeline with SSE streaming."""

import json
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state
from retail_intel.api.schemas import IntelligenceRequest, IntelligenceResponse
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord
from retail_intel.datascience.tier1_rules.deterministic_engine import RuleResolution
from retail_intel.datascience.tier2_ml.cross_encoder import DecisionSplit
from retail_intel.agents.supervisor import ComprehensiveAgentIntelligence

logger = get_logger("api.routes.intelligence")
router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


@router.post("/analyze")
async def analyze_competitor_sku(req: IntelligenceRequest, request: Request):
    """
    Executes the complete Tri-Tier Hybrid Resolution Pipeline:
      Tier 1: Deterministic GTIN + honeypot rules
      Tier 2: Bi-Encoder retrieval + Cross-Encoder scoring
      Tier 3: Multi-agent AI arbitration (if 0.65 <= tau < 0.92)
      Tier 4: HITL escalation (if contradictory or low confidence)
    """
    t0 = time.time()
    # State retrieved via proper FastAPI dependency injection — no circular import
    state = get_app_state(request)

    # 1. Resolve competitor payload
    comp_data: Optional[Dict[str, Any]] = state.competitor_raw_dict.get(req.competitor_sku)
    if not comp_data:
        raise HTTPException(status_code=404, detail=f"Competitor SKU '{req.competitor_sku}' not found in catalog")

    comp_rec: NormalizedProductRecord = state.normalizer.normalize_competitor_payload(comp_data)

    # 2. TIER 1: Deterministic Rules
    rule_res: RuleResolution = state.rule_engine.evaluate(comp_rec)

    if rule_res.is_resolved and not req.force_agentic:
        target_sku = rule_res.internal_sku
        target_rec = state.internal_dict.get(target_sku) if target_sku else None

        # Use real internal product price for anomaly detection — NOT a hardcoded value
        internal_price = target_rec.effective_price if target_rec else comp_rec.effective_price
        internal_raw = target_rec.raw_payload_ref if target_rec else {}
        internal_cogs = float(internal_raw.get("cost_of_goods", internal_price * 0.55))

        anomaly_rep = state.anomaly_detector.evaluate_price_change(
            internal_price=internal_price,
            internal_cogs=internal_cogs,
            competitor_price=comp_rec.effective_price,
        )

        duration = round((time.time() - t0) * 1000, 2)
        state.metrics_engine.record_analysis(verdict=rule_res.verdict or "RESOLVED")
        return {
            "competitor_sku": comp_rec.sku,
            "resolution_tier": "TIER_1_DETERMINISTIC",
            "verdict": rule_res.verdict or "RESOLVED",
            "confidence": rule_res.confidence,
            "target_internal_sku": target_sku,
            "target_internal_title": target_rec.title_clean if target_rec else None,
            "competitor_effective_price": comp_rec.effective_price,
            "internal_price": internal_price,
            "price_anomaly": anomaly_rep.model_dump(),
            "reasoning": rule_res.reason,
            "duration_ms": duration,
            "agentic_intelligence": None,
            "ml_candidates": [],
        }

    # 3. TIER 2: Classical ML (Bi-Encoder + Cross-Encoder)
    t_ret_start = time.time()
    candidates = state.bi_encoder.retrieve_candidates(comp_rec, top_k=req.top_k_candidates)
    retrieval_latency_ms = round((time.time() - t_ret_start) * 1000, 2)

    scored_candidates = []
    top_candidate = None
    for sku, sim, internal_rec in candidates:
        pair_score = state.cross_encoder.score_pair(comp_rec, internal_rec, sim)
        scored_candidates.append(pair_score.model_dump())
        if top_candidate is None:
            top_candidate = (internal_rec, pair_score)

    if not top_candidate:
        duration = round((time.time() - t0) * 1000, 2)
        return {
            "competitor_sku": comp_rec.sku,
            "resolution_tier": "TIER_2_CLASSICAL_ML",
            "verdict": "NO_INTERNAL_EQUIVALENT",
            "confidence": 0.0,
            "target_internal_sku": None,
            "competitor_effective_price": comp_rec.effective_price,
            "reasoning": "No compatible candidates surfaced by retrieval engine.",
            "duration_ms": duration,
            "agentic_intelligence": None,
            "ml_candidates": [],
        }

    best_internal, best_score = top_candidate

    # Anomaly detection using REAL internal product data — fixed hardcoded values bug
    internal_raw = best_internal.raw_payload_ref or {}
    internal_cogs = float(internal_raw.get("cost_of_goods", best_internal.effective_price * 0.55))
    anomaly_rep = state.anomaly_detector.evaluate_price_change(
        internal_price=best_internal.effective_price,
        internal_cogs=internal_cogs,
        competitor_price=comp_rec.effective_price,
    )

    # Tier 2 auto-commit (tau >= 0.92)
    if best_score.decision == DecisionSplit.AUTO_COMMIT and not req.force_agentic:
        duration = round((time.time() - t0) * 1000, 2)
        state.metrics_engine.record_analysis(verdict="DIRECT_SUBSTITUTE")
        return {
            "competitor_sku": comp_rec.sku,
            "resolution_tier": "TIER_2_CLASSICAL_ML",
            "verdict": "DIRECT_SUBSTITUTE",
            "confidence": best_score.score,
            "target_internal_sku": best_internal.sku,
            "target_internal_title": best_internal.title_clean,
            "competitor_effective_price": comp_rec.effective_price,
            "internal_price": best_internal.effective_price,
            "price_anomaly": anomaly_rep.model_dump(),
            "reasoning": f"High-confidence semantic equivalence (tau = {best_score.score}). Auto-committed.",
            "duration_ms": duration,
            "agentic_intelligence": None,
            "ml_candidates": scored_candidates,
        }

    # 4. TIER 3: Multi-Agent AI Escalation (0.65 <= tau < 0.92)
    intelligence: ComprehensiveAgentIntelligence = await state.supervisor.execute_reasoning_flow(
        competitor_rec=comp_rec,
        candidate_internal_rec=best_internal,
        initial_tau=best_score.score,
        internal_cogs=internal_cogs,
    )
    duration = round((time.time() - t0) * 1000, 2)

    # 5. HITL escalation for contradictory or low-confidence outcomes
    escalated_hitl = False
    if intelligence.verdict == "CONTRADICTORY_LISTING" or intelligence.confidence < 0.65:
        escalated_hitl = True
        state.hitl_queue.enqueue_task(
            competitor_sku=comp_rec.sku,
            internal_sku_candidate=best_internal.sku,
            tau_score=intelligence.confidence,
            escalation_reason=intelligence.reasoning_summary,
            agentic_evidence=intelligence.model_dump(exclude={"execution_trace"}),
        )

    state.metrics_engine.record_analysis(
        verdict=intelligence.verdict,
        was_agentic=True,
        was_hitl_escalated=escalated_hitl,
        plan_optimality=intelligence.plan_optimality_ratio,
        gross_margin_protected=intelligence.strategy.gross_margin_protected_usd,
        reflection_applied=intelligence.resolution.reflection_applied,
        tool_success=len(intelligence.resolution.tools_executed),
    )

    return {
        "competitor_sku": comp_rec.sku,
        "resolution_tier": "ESCALATED_HITL" if escalated_hitl else "TIER_3_AGENTIC",
        "verdict": intelligence.verdict,
        "confidence": intelligence.confidence,
        "target_internal_sku": best_internal.sku,
        "target_internal_title": best_internal.title_clean,
        "competitor_effective_price": intelligence.effective_competitor_price,
        "internal_price": best_internal.effective_price,
        "price_anomaly": anomaly_rep.model_dump(),
        "reasoning": intelligence.reasoning_summary,
        "duration_ms": duration,
        "agentic_intelligence": intelligence.model_dump(),
        "ml_candidates": scored_candidates,
    }


@router.get("/stream")
async def stream_reasoning(
    request: Request,
    competitor_sku: Optional[str] = Query(None, description="Competitor SKU to stream thoughts for"),
    sku: Optional[str] = Query(None, description="Alias for competitor_sku"),
):
    """Server-Sent Events (SSE) streaming endpoint for live agent thought trajectories."""
    state = get_app_state(request)
    target_sku = competitor_sku or sku or "ZEN-TV-65-OLED"

    comp_data = state.competitor_raw_dict.get(target_sku)
    if not comp_data and state.competitor_raw_list:
        comp_data = next((c for c in state.competitor_raw_list if c.get("competitor_sku") == target_sku), None)
        if not comp_data:
            comp_data = state.competitor_raw_list[0]

    if not comp_data:
        from retail_intel.data_engineering.dataset_generator import DatasetGenerator
        gen = DatasetGenerator()
        ds = gen.generate_large_scale_dataset(20000)
        state.internal_raw_list = ds["internal_catalog"]
        state.competitor_raw_list = ds["competitor_catalog"]
        state.competitor_raw_dict = {c["competitor_sku"]: c for c in ds["competitor_catalog"]}
        comp_data = state.competitor_raw_dict.get(target_sku, ds["competitor_catalog"][0])

    comp_rec = state.normalizer.normalize_competitor_payload(comp_data)
    candidates = state.bi_encoder.retrieve_candidates(comp_rec, top_k=1)
    if candidates:
        best_internal = candidates[0][2]
    elif state.internal_dict:
        best_internal = list(state.internal_dict.values())[0]
    else:
        # Fallback to normalized internal item
        best_internal = state.normalizer.normalize_internal_product(state.internal_raw_list[0])

    cogs_val = float((best_internal.raw_payload_ref or {}).get("cost_of_goods", best_internal.effective_price * 0.55))

    async def event_generator():
        """True incremental SSE: yields each step as it completes (not buffered)."""
        try:
            async for event in state.supervisor.stream_reasoning_steps(
                comp_rec,
                best_internal,
                initial_tau=0.78,
                internal_cogs=cogs_val,
            ):
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.error("SSE stream encountered error", error=str(exc))
            err_payload = json.dumps({"type": "error", "data": {"message": str(exc)}})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
