"""Autonomous Strategic Reasoning & Causal Impact Agent."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.agents.tools.tool_registry import ToolRegistry
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("agents.strategy")


class StrategicHypothesis(BaseModel):
    competitor_sku: str
    target_internal_sku: str
    causal_intent: str  # "PREDATORY_UNDERCUTTING", "INVENTORY_LIQUIDATION", "PHANTOM_STOCK_LURE", "ROUTINE_COMPETITION"
    gross_margin_protected_usd: float
    margin_destruction_risk_usd: float
    recommended_action: str  # "AUTO_REPRICE", "HOLD_MARGIN", "ISOLATE_PHANTOM", "ESCALATE_HITL"
    strategic_briefing: str
    tools_executed: List[str] = Field(default_factory=list)


class StrategyAgent:
    """Causal reasoning agent evaluating economic intent, margin risk, and counter-actions."""

    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    async def evaluate_strategy(
        self,
        competitor_rec: NormalizedProductRecord,
        internal_rec: NormalizedProductRecord,
        internal_cogs: float = 100.0,
    ) -> StrategicHypothesis:
        """Evaluates causal competitor intent and margin trade-offs."""
        tools_executed = []

        # 1. Verify Fulfillment Viability
        tools_executed.append("verify_fulfillment_inventory")
        fulfill_check = self.tools.verify_fulfillment_inventory(
            competitor_sku=competitor_rec.sku,
            latency_days=competitor_rec.fulfillment_latency_days,
            stock_status=competitor_rec.stock_status,
        )

        c_price = competitor_rec.effective_price
        i_price = internal_rec.effective_price
        diff_usd = i_price - c_price

        # Check Phantom Stock
        if fulfill_check.get("is_phantom_stock"):
            margin_saved = max(0.0, diff_usd) * 50.0  # Estimated 50-unit protection
            return StrategicHypothesis(
                competitor_sku=competitor_rec.sku,
                target_internal_sku=internal_rec.sku,
                causal_intent="PHANTOM_STOCK_LURE",
                gross_margin_protected_usd=round(margin_saved, 2),
                margin_destruction_risk_usd=round(margin_saved, 2),
                recommended_action="ISOLATE_PHANTOM",
                strategic_briefing=(
                    f"Competitor listed ${c_price:.2f} on {competitor_rec.title_clean}, but fulfillment is "
                    f"backordered for {competitor_rec.fulfillment_latency_days} days. This is a phantom stock trap to "
                    f"bait rival repricers. Action: Isolate competitor from dynamic repricer. Protected ${margin_saved:.2f} in gross margin."
                ),
                tools_executed=tools_executed,
            )

        # Check Predatory Undercutting below internal COGS
        if c_price < internal_cogs:
            margin_risk = (i_price - internal_cogs) * 30.0
            return StrategicHypothesis(
                competitor_sku=competitor_rec.sku,
                target_internal_sku=internal_rec.sku,
                causal_intent="PREDATORY_UNDERCUTTING",
                gross_margin_protected_usd=round(margin_risk, 2),
                margin_destruction_risk_usd=round(margin_risk, 2),
                recommended_action="HOLD_MARGIN",
                strategic_briefing=(
                    f"Competitor price of ${c_price:.2f} is below internal COGS (${internal_cogs:.2f}). "
                    f"Matching will induce negative gross margins. Action: Hold price at ${i_price:.2f}, "
                    f"preserving ${margin_risk:.2f} in protected profits."
                ),
                tools_executed=tools_executed,
            )

        # Standard healthy competition
        if c_price < i_price:
            return StrategicHypothesis(
                competitor_sku=competitor_rec.sku,
                target_internal_sku=internal_rec.sku,
                causal_intent="ROUTINE_COMPETITION",
                gross_margin_protected_usd=0.0,
                margin_destruction_risk_usd=round(diff_usd * 20.0, 2),
                recommended_action="AUTO_REPRICE",
                strategic_briefing=(
                    f"Competitor active price ${c_price:.2f} is above COGS (${internal_cogs:.2f}). "
                    f"Action: Auto-reprice internal SKU to ${c_price:.2f} to protect market share."
                ),
                tools_executed=tools_executed,
            )

        return StrategicHypothesis(
            competitor_sku=competitor_rec.sku,
            target_internal_sku=internal_rec.sku,
            causal_intent="ROUTINE_COMPETITION",
            gross_margin_protected_usd=0.0,
            margin_destruction_risk_usd=0.0,
            recommended_action="HOLD_MARGIN",
            strategic_briefing="Internal pricing is already competitive or superior.",
            tools_executed=tools_executed,
        )
