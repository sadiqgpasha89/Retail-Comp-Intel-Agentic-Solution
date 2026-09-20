"""Master Supervisor Agent: Plan-Execute-Reflect-Report multi-agent orchestrator."""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import BaseModel, Field

from retail_intel.core.config import settings
from retail_intel.core.logging import get_logger
from retail_intel.agents.tools.tool_registry import ToolRegistry
from retail_intel.agents.matcher_agent import MatcherAgent, MatcherResolution
from retail_intel.agents.promo_agent import PromoAgent, PromoDissectionResult
from retail_intel.agents.strategy_agent import StrategyAgent, StrategicHypothesis
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("agents.supervisor")


class AgentStepLog(BaseModel):
    step_number: int
    phase: str  # "PLAN", "EXECUTE", "REFLECT", "REPORT"
    agent: str  # "Supervisor", "Matcher", "Promo", "Strategy", "Reflection"
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float
    timestamp: float = Field(default_factory=time.time)


class ComprehensiveAgentIntelligence(BaseModel):
    competitor_sku: str
    target_internal_sku: Optional[str]
    verdict: str  # "EXACT_MATCH", "EQUIVALENT_PRIVATE_LABEL", "DIRECT_SUBSTITUTE", "UNFULFILLED_PHANTOM", "CONTRADICTORY_LISTING", "HONEYPOT_TRAP"
    confidence: float
    effective_competitor_price: float
    normalized_unit_price: float
    promotions: PromoDissectionResult
    strategy: StrategicHypothesis
    resolution: MatcherResolution
    plan_optimality_ratio: float
    total_steps_executed: int
    optimal_steps: int
    reasoning_summary: str
    execution_trace: List[AgentStepLog] = Field(default_factory=list)


class SupervisorAgent:
    """Master Multi-Agent Orchestrator executing dynamic goal decomposition and reflection loops."""

    def __init__(self, tools: Optional[ToolRegistry] = None):
        self.tools = tools or ToolRegistry()
        self.matcher = MatcherAgent(self.tools)
        self.promo = PromoAgent(self.tools)
        self.strategy = StrategyAgent(self.tools)

    async def execute_reasoning_flow(
        self,
        competitor_rec: NormalizedProductRecord,
        candidate_internal_rec: NormalizedProductRecord,
        initial_tau: float,
        internal_cogs: float = 100.0,
    ) -> ComprehensiveAgentIntelligence:
        """Executes full Plan-Execute-Reflect-Report lifecycle."""
        logs: List[AgentStepLog] = []
        step_idx = 0

        # Step 1: PLAN Phase
        t0 = time.time()
        step_idx += 1
        sub_tasks = [
            "Deconstruct promotional coupon & cart discounts",
            "Verify fulfillment availability & phantom stock signals",
            "Arbitrate borderline entity equivalence & inspect OEM patents",
            "Evaluate causal economic intent & gross margin risk",
        ]
        logs.append(AgentStepLog(
            step_number=step_idx,
            phase="PLAN",
            agent="Supervisor",
            action="Decompose ambiguous SKU resolution into verifiable sub-tasks",
            details={"sub_tasks": sub_tasks, "step_budget": settings.agent_step_budget},
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))

        # Step 2: EXECUTE — Promo Agent
        t0 = time.time()
        step_idx += 1
        promo_res: PromoDissectionResult = await self.promo.dissect_promotions(competitor_rec)
        logs.append(AgentStepLog(
            step_number=step_idx,
            phase="EXECUTE",
            agent="PromoAgent",
            action="Simulate checkout and discover basket discount",
            details={
                "effective_price": promo_res.final_effective_price,
                "mechanic": promo_res.promotional_mechanic,
                "map_evaded": promo_res.is_map_policy_evaded,
            },
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))

        # Step 3: EXECUTE — Matcher Agent
        t0 = time.time()
        step_idx += 1
        matcher_res: MatcherResolution = await self.matcher.arbitrate_match(
            competitor_rec, candidate_internal_rec, initial_tau
        )
        logs.append(AgentStepLog(
            step_number=step_idx,
            phase="EXECUTE",
            agent="MatcherAgent",
            action="Arbitrate SKU equivalence using tools & Knowledge Graph",
            details={
                "match_type": matcher_res.match_type,
                "confidence": matcher_res.confidence,
                "tools": matcher_res.tools_executed,
            },
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))

        # Step 4: REFLECT Phase
        t0 = time.time()
        step_idx += 1
        reflection_applied = matcher_res.reflection_applied
        logs.append(AgentStepLog(
            step_number=step_idx,
            phase="REFLECT",
            agent="ReflectionGuard",
            action="Audit evidence consistency against 4-Tier Hierarchy of Truth",
            details={
                "hierarchy_applied": "Tier 1 Review Imagery > Tier 4 Title" if reflection_applied else "Consistent",
                "correction_applied": reflection_applied,
                "audit_notes": matcher_res.reasoning,
            },
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))

        # Step 5: EXECUTE — Strategy Agent
        t0 = time.time()
        step_idx += 1
        strat_res: StrategicHypothesis = await self.strategy.evaluate_strategy(
            competitor_rec, candidate_internal_rec, internal_cogs=internal_cogs
        )
        logs.append(AgentStepLog(
            step_number=step_idx,
            phase="EXECUTE",
            agent="StrategyAgent",
            action="Synthesize causal hypothesis and model margin impact",
            details={
                "causal_intent": strat_res.causal_intent,
                "recommended_action": strat_res.recommended_action,
                "margin_protected": strat_res.gross_margin_protected_usd,
            },
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))

        # Step 6: REPORT Phase
        t0 = time.time()
        step_idx += 1
        optimal_steps = 4
        plan_optimality = round(optimal_steps / step_idx, 4)

        # Final verdict determination
        if strat_res.causal_intent == "PHANTOM_STOCK_LURE":
            verdict = "UNFULFILLED_PHANTOM"
        elif matcher_res.match_type == "CONTRADICTORY_LISTING":
            verdict = "CONTRADICTORY_LISTING"
        elif matcher_res.match_type == "EQUIVALENT_PRIVATE_LABEL":
            verdict = "EQUIVALENT_PRIVATE_LABEL"
        elif matcher_res.match_type == "EXACT_MATCH":
            verdict = "EXACT_MATCH"
        else:
            verdict = "DIRECT_SUBSTITUTE"

        logs.append(AgentStepLog(
            step_number=step_idx,
            phase="REPORT",
            agent="Supervisor",
            action="Synthesize structured intelligence payload & audit rationale",
            details={"verdict": verdict, "plan_optimality": plan_optimality},
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))

        summary = (
            f"Autonomous arbitration determined {competitor_rec.sku} is '{verdict}' "
            f"against internal SKU {candidate_internal_rec.sku} (Confidence: {matcher_res.confidence * 100:.1f}%). "
            f"Causal Intent: {strat_res.causal_intent}. Action: {strat_res.recommended_action}. "
            f"Protected Margin: ${strat_res.gross_margin_protected_usd:.2f}."
        )

        return ComprehensiveAgentIntelligence(
            competitor_sku=competitor_rec.sku,
            target_internal_sku=candidate_internal_rec.sku,
            verdict=verdict,
            confidence=matcher_res.confidence,
            effective_competitor_price=promo_res.final_effective_price,
            normalized_unit_price=matcher_res.normalized_unit_price,
            promotions=promo_res,
            strategy=strat_res,
            resolution=matcher_res,
            plan_optimality_ratio=plan_optimality,
            total_steps_executed=step_idx,
            optimal_steps=optimal_steps,
            reasoning_summary=summary,
            execution_trace=logs,
        )

    async def stream_reasoning_steps(
        self,
        competitor_rec: NormalizedProductRecord,
        candidate_internal_rec: NormalizedProductRecord,
        initial_tau: float,
        internal_cogs: float = 100.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        True incremental SSE streaming: yields each reasoning step as it completes
        rather than buffering everything and emitting at the end.
        """
        logs: List[AgentStepLog] = []
        step_idx = 0

        # Step 1: PLAN
        t0 = time.time()
        step_idx += 1
        sub_tasks = [
            "Deconstruct promotional coupon & cart discounts",
            "Verify fulfillment availability & phantom stock signals",
            "Arbitrate borderline entity equivalence & inspect OEM patents",
            "Evaluate causal economic intent & gross margin risk",
        ]
        step = AgentStepLog(
            step_number=step_idx,
            phase="PLAN",
            agent="Supervisor",
            action="Decompose ambiguous SKU resolution into verifiable sub-tasks",
            details={"sub_tasks": sub_tasks, "step_budget": settings.agent_step_budget},
            duration_ms=round((time.time() - t0) * 1000, 2),
        )
        logs.append(step)
        yield {"type": "step", "data": step.model_dump()}
        await asyncio.sleep(0.04)

        # Step 2: EXECUTE — Promo
        t0 = time.time()
        step_idx += 1
        promo_res = await self.promo.dissect_promotions(competitor_rec)
        step = AgentStepLog(
            step_number=step_idx,
            phase="EXECUTE",
            agent="PromoAgent",
            action="Simulate checkout and discover basket discount",
            details={"effective_price": promo_res.final_effective_price},
            duration_ms=round((time.time() - t0) * 1000, 2),
        )
        logs.append(step)
        yield {"type": "step", "data": step.model_dump()}
        await asyncio.sleep(0.04)

        # Step 3: EXECUTE — Matcher
        t0 = time.time()
        step_idx += 1
        matcher_res = await self.matcher.arbitrate_match(competitor_rec, candidate_internal_rec, initial_tau)
        step = AgentStepLog(
            step_number=step_idx,
            phase="EXECUTE",
            agent="MatcherAgent",
            action="Arbitrate SKU equivalence using tools & Knowledge Graph",
            details={"match_type": matcher_res.match_type, "confidence": matcher_res.confidence},
            duration_ms=round((time.time() - t0) * 1000, 2),
        )
        logs.append(step)
        yield {"type": "step", "data": step.model_dump()}
        await asyncio.sleep(0.04)

        # Step 4: REFLECT
        t0 = time.time()
        step_idx += 1
        step = AgentStepLog(
            step_number=step_idx,
            phase="REFLECT",
            agent="ReflectionGuard",
            action="Audit evidence consistency against 4-Tier Hierarchy of Truth",
            details={"correction_applied": matcher_res.reflection_applied},
            duration_ms=round((time.time() - t0) * 1000, 2),
        )
        logs.append(step)
        yield {"type": "step", "data": step.model_dump()}
        await asyncio.sleep(0.04)

        # Step 5: EXECUTE — Strategy
        t0 = time.time()
        step_idx += 1
        strat_res = await self.strategy.evaluate_strategy(
            competitor_rec, candidate_internal_rec, internal_cogs=internal_cogs
        )
        step = AgentStepLog(
            step_number=step_idx,
            phase="EXECUTE",
            agent="StrategyAgent",
            action="Synthesize causal hypothesis and model margin impact",
            details={"causal_intent": strat_res.causal_intent, "recommended_action": strat_res.recommended_action},
            duration_ms=round((time.time() - t0) * 1000, 2),
        )
        logs.append(step)
        yield {"type": "step", "data": step.model_dump()}
        await asyncio.sleep(0.04)

        # Step 6: REPORT (final intelligence payload)
        optimal_steps = 4
        if strat_res.causal_intent == "PHANTOM_STOCK_LURE":
            verdict = "UNFULFILLED_PHANTOM"
        elif matcher_res.match_type == "CONTRADICTORY_LISTING":
            verdict = "CONTRADICTORY_LISTING"
        elif matcher_res.match_type == "EQUIVALENT_PRIVATE_LABEL":
            verdict = "EQUIVALENT_PRIVATE_LABEL"
        elif matcher_res.match_type == "EXACT_MATCH":
            verdict = "EXACT_MATCH"
        else:
            verdict = "DIRECT_SUBSTITUTE"

        intelligence = ComprehensiveAgentIntelligence(
            competitor_sku=competitor_rec.sku,
            target_internal_sku=candidate_internal_rec.sku,
            verdict=verdict,
            confidence=matcher_res.confidence,
            effective_competitor_price=promo_res.final_effective_price,
            normalized_unit_price=matcher_res.normalized_unit_price,
            promotions=promo_res,
            strategy=strat_res,
            resolution=matcher_res,
            plan_optimality_ratio=round(optimal_steps / step_idx, 4),
            total_steps_executed=step_idx,
            optimal_steps=optimal_steps,
            reasoning_summary=(
                f"Autonomous arbitration determined {competitor_rec.sku} is '{verdict}' "
                f"against internal SKU {candidate_internal_rec.sku}."
            ),
            execution_trace=logs,
        )
        yield {"type": "complete", "data": intelligence.model_dump()}
