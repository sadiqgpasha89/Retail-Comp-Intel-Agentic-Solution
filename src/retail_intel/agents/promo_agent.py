"""Promotional & Cart Dissection Agent: discovers hidden basket discounts, vouchers, and MAP evasion."""

from typing import List, Optional

from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.agents.tools.tool_registry import ToolRegistry
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("agents.promo")


class PromoDissectionResult(BaseModel):
    competitor_sku: str
    base_msrp: float
    coupon_clipped: float
    cart_discount: float
    final_effective_price: float
    effective_discount_pct: float
    is_map_policy_evaded: bool
    promotional_mechanic: str  # "BASE_ONLY", "ON_PAGE_COUPON", "DYNAMIC_BASKET_DISCOUNT", "TIERED_VOLUME"
    tools_executed: List[str] = Field(default_factory=list)


class PromoAgent:
    """Specialized shopper agent evaluating dynamic checkout promotions."""

    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    async def dissect_promotions(self, competitor_rec: NormalizedProductRecord) -> PromoDissectionResult:
        """Executes simulated checkout and promotional coupon discovery."""
        raw_ref = competitor_rec.raw_payload_ref or {}
        on_page_coupon = float(raw_ref.get("on_page_coupon", 0.0))
        cart_discount = float(raw_ref.get("cart_discount", 0.0))

        sim_output = self.tools.simulate_checkout_basket(
            pdp_url=competitor_rec.pdp_url,
            base_price=competitor_rec.base_price,
            on_page_coupon=on_page_coupon,
            cart_discount=cart_discount,
        )

        total_discount = on_page_coupon + cart_discount
        discount_pct = (total_discount / max(0.01, competitor_rec.base_price)) * 100

        if cart_discount > 0:
            mechanic = "DYNAMIC_BASKET_DISCOUNT"
        elif on_page_coupon > 0:
            mechanic = "ON_PAGE_COUPON"
        else:
            mechanic = "BASE_ONLY"

        return PromoDissectionResult(
            competitor_sku=competitor_rec.sku,
            base_msrp=competitor_rec.base_price,
            coupon_clipped=on_page_coupon,
            cart_discount=cart_discount,
            final_effective_price=sim_output["final_checkout_price"],
            effective_discount_pct=round(discount_pct, 2),
            is_map_policy_evaded=sim_output["map_policy_evasion_flag"],
            promotional_mechanic=mechanic,
            tools_executed=["simulate_checkout_basket"],
        )
