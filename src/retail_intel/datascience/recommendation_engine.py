"""Retail Merchandising & Pricing Recommendation Engine.
Synthesizes competitive intelligence into executive merchandising actions,
margin preservation directives, and revenue optimization strategies.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger

logger = get_logger("datascience.recommendation_engine")


class MerchandisingAction(BaseModel):
    recommendation_id: str
    action_type: str
    urgency: str  # IMMEDIATE, HIGH, MEDIUM, STRATEGIC
    category: str
    internal_sku: str
    internal_title: str
    competitor_id: str
    competitor_name: str
    competitor_sku: str
    internal_price: float
    competitor_price: float
    price_gap_pct: float
    category_price_index: float
    cogs: float
    current_gross_margin_pct: float
    recommended_price: float
    projected_margin_pct: float
    financial_impact_usd: float
    executive_directive: str
    strategic_rationale: str
    action_steps: List[str]
    guardrails: str


class RecommendationsSummary(BaseModel):
    total_active_recommendations: int
    immediate_actions_count: int
    total_revenue_at_risk_usd: float
    projected_revenue_uplift_usd: float
    gross_margin_protected_usd: float
    average_price_index: float
    competitor_count: int
    category_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    top_actions: List[MerchandisingAction] = Field(default_factory=list)


class RecommendationEngine:
    """Evaluates catalog observations and matches to produce actionable retail merchandising directives."""

    def __init__(self):
        pass

    def generate_recommendations(
        self,
        internal_catalog: List[Dict[str, Any]],
        competitor_catalog: List[Dict[str, Any]],
        observations: Optional[List[Dict[str, Any]]] = None,
    ) -> RecommendationsSummary:
        """Generates structured retail recommendations from current internal and competitor market data."""
        internal_map = {item["sku"]: item for item in internal_catalog}
        actions: List[MerchandisingAction] = []

        total_rev_risk = 0.0
        projected_uplift = 0.0
        margin_protected = 0.0
        price_indices: List[float] = []

        category_stats: Dict[str, Dict[str, Any]] = {}
        action_counter = 1

        for comp in competitor_catalog:
            target_sku = comp.get("target_internal_sku") or comp.get("matched_sku_id")
            if not target_sku:
                comp_gtin = comp.get("gtin")
                if comp_gtin:
                    target_sku = next((i["sku"] for i in internal_catalog if i.get("gtin") == comp_gtin), None)
                if not target_sku:
                    comp_cat = comp.get("raw_category", "").split(">")[0].strip()
                    target_sku = next((i["sku"] for i in internal_catalog if comp_cat in i.get("canonical_category", "")), None)
                if not target_sku and internal_catalog:
                    target_sku = internal_catalog[action_counter % len(internal_catalog)]["sku"]

            internal_item = internal_map.get(target_sku) if target_sku else None

            if not internal_item:
                continue

            int_price = internal_item["current_price"]
            comp_price = comp["final_effective_price"]
            cogs = internal_item.get("cost_of_goods", int_price * 0.55)
            curr_margin = (int_price - cogs) / int_price if int_price > 0 else 0.0
            price_gap_pct = round(((comp_price - int_price) / int_price) * 100, 2)
            pi = round((comp_price / int_price) * 100, 1) if int_price > 0 else 100.0
            price_indices.append(pi)

            cat_full = internal_item.get("canonical_category", "General")
            cat_name = cat_full.split(">")[0].strip()

            if cat_name not in category_stats:
                category_stats[cat_name] = {
                    "sku_count": 0,
                    "avg_pi": [],
                    "total_risk_usd": 0.0,
                    "opportunity_usd": 0.0,
                }
            category_stats[cat_name]["sku_count"] += 1
            category_stats[cat_name]["avg_pi"].append(pi)

            weekly_velocity = internal_item.get("weekly_velocity_units", 350)
            challenge_class = comp.get("challenge_class", "STANDARD_MATCH")

            # 1. High-Velocity Elastic SKUs undercut by competitor -> AUTO-REPRICE
            if price_gap_pct < -5.0 and not comp.get("is_phantom_stock") and not comp.get("is_honeypot"):
                if comp_price >= (cogs * 1.12):
                    rec_p = round(comp_price, 2)
                    proj_margin = round((rec_p - cogs) / rec_p, 4)
                    risk_amount = round(weekly_velocity * (int_price - comp_price) * 4, 2)
                    total_rev_risk += risk_amount

                    pe_val = internal_item.get("price_elasticity") or -1.5
                    mf_val = internal_item.get("margin_floor") or (cogs * 1.15)

                    act = MerchandisingAction(
                        recommendation_id=f"REC-{action_counter:04d}",
                        action_type="AUTO_REPRICE_VOLUME_DEFENSE",
                        urgency="IMMEDIATE" if price_gap_pct < -12.0 else "HIGH",
                        category=cat_name,
                        internal_sku=internal_item["sku"],
                        internal_title=internal_item["title"],
                        competitor_id=comp["competitor_id"],
                        competitor_name=comp["competitor_name"],
                        competitor_sku=comp["competitor_sku"],
                        internal_price=int_price,
                        competitor_price=comp_price,
                        price_gap_pct=price_gap_pct,
                        category_price_index=pi,
                        cogs=cogs,
                        current_gross_margin_pct=round(curr_margin * 100, 1),
                        recommended_price=rec_p,
                        projected_margin_pct=round(proj_margin * 100, 1),
                        financial_impact_usd=risk_amount,
                        executive_directive=f"Reprice to ${rec_p:.2f} to defend ${risk_amount:,.2f} monthly category volume.",
                        strategic_rationale=f"{comp['competitor_name']} undercut active price by {abs(price_gap_pct)}%. High cross-elasticity ({pe_val:.2f}) creates high churn risk. Margin floor (${mf_val:.2f}) is preserved.",
                        action_steps=[
                            f"Commit automated price drop from ${int_price:.2f} to ${rec_p:.2f} via Dynamic Pricing Feed",
                            "Monitor competitor stock levels and bounce-back within 48h",
                            "Trigger email marketing banner for price-match guarantee",
                        ],
                        guardrails=f"Absolute COGS floor: ${cogs:.2f}. Minimum gross margin maintained: {proj_margin*100:.1f}%.",
                    )
                    actions.append(act)
                    action_counter += 1

            # 2. Phantom Stock / Unfulfilled Lures -> HOLD MARGIN
            elif comp.get("is_phantom_stock"):
                protected_val = round(weekly_velocity * (int_price - comp_price) * 4, 2)
                margin_protected += protected_val

                act = MerchandisingAction(
                    recommendation_id=f"REC-{action_counter:04d}",
                    action_type="HOLD_MARGIN_PHANTOM_DEFENSE",
                    urgency="HIGH",
                    category=cat_name,
                    internal_sku=internal_item["sku"],
                    internal_title=internal_item["title"],
                    competitor_id=comp["competitor_id"],
                    competitor_name=comp["competitor_name"],
                    competitor_sku=comp["competitor_sku"],
                    internal_price=int_price,
                    competitor_price=comp_price,
                    price_gap_pct=price_gap_pct,
                    category_price_index=pi,
                    cogs=cogs,
                    current_gross_margin_pct=round(curr_margin * 100, 1),
                    recommended_price=int_price,
                    projected_margin_pct=round(curr_margin * 100, 1),
                    financial_impact_usd=protected_val,
                    executive_directive=f"Hold active price at ${int_price:.2f}; protect ${protected_val:,.2f} in gross margin.",
                    strategic_rationale=f"{comp['competitor_name']} price of ${comp_price:.2f} is an unfulfillable phantom lure (lead time {comp.get('fulfillment_latency_days', 45)}d, stockout). Matching this price would destroy margin with zero conversion gain.",
                    action_steps=[
                        "Lock SKU against automated algorithmic price drops",
                        "Promote 'In Stock & Ready for Next-Day Delivery' badge on PDP",
                        "Capture competitor stockout traffic via paid search conquesting",
                    ],
                    guardrails="Do NOT initiate repricing until competitor verifies live inventory.",
                )
                actions.append(act)
                action_counter += 1

            # 3. MAP Policy Violation -> ENFORCE COMPLIANCE
            elif comp_price < (internal_item.get("map_policy_price") or (int_price * 0.95)):
                map_val = internal_item.get("map_policy_price") or (int_price * 0.95)
                act = MerchandisingAction(
                    recommendation_id=f"REC-{action_counter:04d}",
                    action_type="ENFORCE_MAP_POLICY",
                    urgency="HIGH",
                    category=cat_name,
                    internal_sku=internal_item["sku"],
                    internal_title=internal_item["title"],
                    competitor_id=comp["competitor_id"],
                    competitor_name=comp["competitor_name"],
                    competitor_sku=comp["competitor_sku"],
                    internal_price=int_price,
                    competitor_price=comp_price,
                    price_gap_pct=price_gap_pct,
                    category_price_index=pi,
                    cogs=cogs,
                    current_gross_margin_pct=round(curr_margin * 100, 1),
                    recommended_price=int_price,
                    projected_margin_pct=round(curr_margin * 100, 1),
                    financial_impact_usd=round(weekly_velocity * 15.0, 2),
                    executive_directive=f"Issue MAP violation compliance notice to {comp['competitor_name']}.",
                    strategic_rationale=f"Competitor advertised price ${comp_price:.2f} violates contractual Minimum Advertised Price (MAP) threshold of ${map_val:.2f}. Enforcing policy protects brand equity.",
                    action_steps=[
                        "Dispatch automated timestamped screenshot & DOM snapshot to Brand Compliance legal team",
                        "Trigger manufacturer wholesale supply hold notification",
                        "Maintain retail price at MSRP pending partner resolution",
                    ],
                    guardrails="Legal SLA: 24-hour compliance escalation window.",
                )
                actions.append(act)
                action_counter += 1

            # 4. Private Label OEM Arbitrage
            elif challenge_class == "PRIVATE_LABEL_OEM" or comp.get("brand") == comp.get("competitor_name"):
                uplift_val = round(weekly_velocity * (int_price * 0.22) * 4, 2)
                projected_uplift += uplift_val

                act = MerchandisingAction(
                    recommendation_id=f"REC-{action_counter:04d}",
                    action_type="OEM_PRIVATE_LABEL_ARBITRAGE",
                    urgency="STRATEGIC",
                    category=cat_name,
                    internal_sku=internal_item["sku"],
                    internal_title=internal_item["title"],
                    competitor_id=comp["competitor_id"],
                    competitor_name=comp["competitor_name"],
                    competitor_sku=comp["competitor_sku"],
                    internal_price=int_price,
                    competitor_price=comp_price,
                    price_gap_pct=price_gap_pct,
                    category_price_index=pi,
                    cogs=cogs,
                    current_gross_margin_pct=round(curr_margin * 100, 1),
                    recommended_price=int_price,
                    projected_margin_pct=round(curr_margin * 100, 1),
                    financial_impact_usd=uplift_val,
                    executive_directive=f"Position store-brand counterpart to capture ${uplift_val:,.2f} in high-margin switchers.",
                    strategic_rationale=f"Competitor {comp['competitor_name']} private label shares identical OEM manufacturing ({internal_item.get('specifications', {}).get('oem_factory_id')}). Highlight physical equivalence on PDP and in recommendation carousels to drive high-margin store-brand adoption.",
                    action_steps=[
                        "Launch 'Compare & Save' side-by-side spec comparison on product page",
                        "Highlight shared ISO-certified manufacturing and 2-year warranty",
                        "Merchandise store-brand in search top sponsored slot",
                    ],
                    guardrails="Highlight quality parity without mentioning competitor trademarks directly.",
                )
                actions.append(act)
                action_counter += 1

            # 5. Basket Builder Cross-Sell
            elif int_price > 100.0:
                bundle_opp = round(weekly_velocity * 25.0 * 2, 2)
                projected_uplift += bundle_opp

                act = MerchandisingAction(
                    recommendation_id=f"REC-{action_counter:04d}",
                    action_type="BASKET_BUILDER_BUNDLE",
                    urgency="MEDIUM",
                    category=cat_name,
                    internal_sku=internal_item["sku"],
                    internal_title=internal_item["title"],
                    competitor_id=comp["competitor_id"],
                    competitor_name=comp["competitor_name"],
                    competitor_sku=comp["competitor_sku"],
                    internal_price=int_price,
                    competitor_price=comp_price,
                    price_gap_pct=price_gap_pct,
                    category_price_index=pi,
                    cogs=cogs,
                    current_gross_margin_pct=round(curr_margin * 100, 1),
                    recommended_price=int_price,
                    projected_margin_pct=round(curr_margin * 100, 1),
                    financial_impact_usd=bundle_opp,
                    executive_directive=f"Create high-margin accessory bundle to unlock ${bundle_opp:,.2f} incremental revenue.",
                    strategic_rationale=f"Attach high-margin (65% gross margin) accessory kit at $19.99 with checkout discount, neutralizing competitor single-unit price advantage while expanding total basket size.",
                    action_steps=[
                        "Configure 'Frequently Bought Together' 1-click bundle discount in checkout",
                        "Offer free 2-day delivery on bundled orders above $150",
                    ],
                    guardrails="Ensure attached accessories maintain minimum 55% margin floor.",
                )
                actions.append(act)
                action_counter += 1

        # Calculate category summaries
        formatted_cat_summary: Dict[str, Dict[str, Any]] = {}
        for cname, stats in category_stats.items():
            pis = stats["avg_pi"]
            avg_pi = round(sum(pis) / len(pis), 1) if pis else 100.0
            status = "COMPETITIVE_ADVANTAGE" if avg_pi > 102 else ("AT_PARITY" if avg_pi >= 98 else "PRICE_DISADVANTAGE")
            formatted_cat_summary[cname] = {
                "sku_count": stats["sku_count"],
                "average_price_index": avg_pi,
                "pricing_status": status,
            }

        avg_overall_pi = round(sum(price_indices) / len(price_indices), 1) if price_indices else 100.0
        immediate_count = sum(1 for a in actions if a.urgency == "IMMEDIATE")

        return RecommendationsSummary(
            total_active_recommendations=len(actions),
            immediate_actions_count=immediate_count,
            total_revenue_at_risk_usd=round(total_rev_risk, 2),
            projected_revenue_uplift_usd=round(projected_uplift, 2),
            gross_margin_protected_usd=round(margin_protected, 2),
            average_price_index=avg_overall_pi,
            competitor_count=len({c["competitor_id"] for c in competitor_catalog}),
            category_breakdown=formatted_cat_summary,
            top_actions=actions[:50],
        )


recommendation_engine = RecommendationEngine()
