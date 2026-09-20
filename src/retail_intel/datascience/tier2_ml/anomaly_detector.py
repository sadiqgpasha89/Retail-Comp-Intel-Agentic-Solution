"""Pricing Anomaly Detection: Isolation Forest & statistical outlier detection for predatory drops and bot oscillation."""

from typing import Optional

import numpy as np
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest

from retail_intel.core.logging import get_logger

logger = get_logger("datascience.tier2_ml.anomaly")


class PriceAnomalyReport(BaseModel):
    is_anomaly: bool
    anomaly_type: Optional[str] = None  # "PREDATORY_PRICING", "EXTREME_DROP", "REPRICER_OSCILLATION"
    severity_score: float  # 0.0 to 1.0
    price_change_pct: float
    description: str


class PricingAnomalyDetector:
    """Detects predatory price undercutting, algorithmic glitches, and severe price shifts."""

    def __init__(self, contamination: float = 0.05):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        baseline_data = np.array([
            [-0.05, 1.0], [-0.10, 0.95], [-0.15, 0.90], [0.0, 1.05],
            [0.05, 1.10], [-0.20, 0.85], [-0.02, 1.01], [-0.08, 0.96],
        ])
        self.model.fit(baseline_data)

    def evaluate_price_change(
        self,
        internal_price: float,
        internal_cogs: float,
        competitor_price: float,
        historical_competitor_price: Optional[float] = None,
    ) -> PriceAnomalyReport:
        """Evaluates price discrepancy against internal cost and historical benchmarks."""
        ref_price = historical_competitor_price or internal_price
        diff_pct = (competitor_price - ref_price) / max(0.01, ref_price)

        price_to_cogs = competitor_price / max(0.01, internal_cogs)
        feature_vec = np.array([[diff_pct, price_to_cogs]])

        iso_score = self.model.decision_function(feature_vec)[0]
        is_outlier = iso_score < 0

        if competitor_price < internal_cogs * 0.70:
            return PriceAnomalyReport(
                is_anomaly=True,
                anomaly_type="PREDATORY_PRICING",
                severity_score=round(float(min(1.0, 0.5 + abs(diff_pct))), 3),
                price_change_pct=round(diff_pct * 100, 2),
                description=f"Price ${competitor_price:.2f} is significantly below internal COGS (${internal_cogs:.2f}). Severe margin destruction risk.",
            )
        elif diff_pct <= -0.40:
            return PriceAnomalyReport(
                is_anomaly=True,
                anomaly_type="EXTREME_DROP",
                severity_score=round(float(min(1.0, abs(diff_pct))), 3),
                price_change_pct=round(diff_pct * 100, 2),
                description=f"Sharp price reduction of {abs(diff_pct) * 100:.1f}%. Possible clearance event or scraper honeypot.",
            )
        elif is_outlier:
            return PriceAnomalyReport(
                is_anomaly=True,
                anomaly_type="STATISTICAL_OUTLIER",
                severity_score=0.65,
                price_change_pct=round(diff_pct * 100, 2),
                description="Isolation Forest flagged price point as a multidimensional anomaly.",
            )

        return PriceAnomalyReport(
            is_anomaly=False,
            severity_score=0.0,
            price_change_pct=round(diff_pct * 100, 2),
            description="Price change is within normal market oscillation tolerances.",
        )
