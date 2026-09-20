"""Comprehensive Drift Radar: PSI (Covariate Shift), Wasserstein (Embedding Drift), and Page-Hinkley (Concept Drift)."""

import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field
from scipy.stats import wasserstein_distance

from retail_intel.core.config import settings
from retail_intel.core.logging import get_logger

logger = get_logger("mlops.drift_radar")


class DriftReport(BaseModel):
    """Encapsulates statistical drift metrics across features, embeddings, and concepts."""
    timestamp: float
    psi_score: float
    psi_status: str  # "STABLE", "WARNING", "CRITICAL"
    wasserstein_embedding_distance: float
    wasserstein_distance: float = 0.038
    embedding_drift_status: str  # "STABLE" or "DRIFT_DETECTED"
    page_hinkley_statistic: float
    page_hinkley_stat: float = 0.0
    concept_drift_detected: bool
    summary: str
    feature_psi_breakdown: Dict[str, float] = Field(default_factory=dict)


class PageHinkleyTest:
    """Sequential analysis test for concept drift on classification residual error."""
    def __init__(self, delta: float = 0.05, threshold: float = 2.0, alpha: float = 0.99):
        self.delta = delta
        self.threshold = threshold
        self.alpha = alpha
        self.baseline_mean: float = 0.05
        self.cumulative_sum: float = 0.0
        self.min_cumulative: float = 0.0
        self.sample_count: int = 0

    def update(self, error_value: float) -> bool:
        """Updates the test with latest error (0.0 for match, 1.0 for mismatch). Returns True if drift detected."""
        self.sample_count += 1
        dev = error_value - self.baseline_mean - self.delta
        self.cumulative_sum = max(0.0, self.alpha * self.cumulative_sum + dev)
        if self.cumulative_sum < self.min_cumulative:
            self.min_cumulative = self.cumulative_sum

        ph_stat = self.cumulative_sum - self.min_cumulative
        return ph_stat > self.threshold

    @property
    def current_stat(self) -> float:
        return max(0.0, self.cumulative_sum - self.min_cumulative)


class DriftRadar:
    """Enterprise Statistical Drift Radar for Retail Competitor Feeds."""
    def __init__(self):
        self.ph_test = PageHinkleyTest(threshold=settings.page_hinkley_threshold)
        self.historical_prices: List[float] = [299.99, 1799.99, 14.99, 13.99, 429.00, 129.00, 199.99, 329.99]
        self.historical_embeddings: Optional[np.ndarray] = None

    @staticmethod
    def calculate_psi(baseline: np.ndarray, target: np.ndarray, num_bins: int = 5) -> float:
        """Calculates Population Stability Index (PSI): sum((P_i - Q_i) * ln(P_i / Q_i))."""
        if len(baseline) == 0 or len(target) == 0:
            return 0.0

        combined = np.concatenate([baseline, target])
        quantiles = np.linspace(0, 100, num_bins + 1)
        bin_edges = np.percentile(combined, quantiles)
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            return 0.0

        b_counts, _ = np.histogram(baseline, bins=bin_edges)
        t_counts, _ = np.histogram(target, bins=bin_edges)

        eps = 1e-4
        b_pct = (b_counts + eps) / (len(baseline) + eps * len(b_counts))
        t_pct = (t_counts + eps) / (len(target) + eps * len(t_counts))

        psi_val = np.sum((t_pct - b_pct) * np.log(t_pct / b_pct))
        return float(max(0.0, psi_val))

    def evaluate_embedding_drift(self, current_embeddings: np.ndarray) -> Tuple[float, str]:
        """Calculates 1D Wasserstein distance across mean vector dimensions."""
        if self.historical_embeddings is None or len(current_embeddings) == 0:
            self.historical_embeddings = current_embeddings
            return 0.0, "STABLE"

        base_mean = np.mean(self.historical_embeddings, axis=0)
        curr_mean = np.mean(current_embeddings, axis=0)
        w_dist = float(wasserstein_distance(base_mean, curr_mean))

        status = "DRIFT_DETECTED" if w_dist >= settings.wasserstein_drift_threshold else "STABLE"
        return w_dist, status

    def record_match_feedback(self, is_correct: bool) -> bool:
        """Feeds error signal into Page-Hinkley test."""
        error_val = 0.0 if is_correct else 1.0
        return self.ph_test.update(error_val)

    def run_comprehensive_audit(
        self, current_prices: List[float], current_embeddings: Optional[np.ndarray] = None
    ) -> DriftReport:
        """Executes end-to-end drift audit across price distribution, embeddings, and concept health."""
        base_arr = np.array(self.historical_prices, dtype=np.float32)
        curr_arr = np.array(current_prices if current_prices else self.historical_prices, dtype=np.float32)

        price_psi = self.calculate_psi(base_arr, curr_arr)
        if price_psi < settings.psi_warning_threshold:
            psi_status = "STABLE"
        elif price_psi < settings.psi_critical_threshold:
            psi_status = "WARNING"
        else:
            psi_status = "CRITICAL"

        w_dist = 0.04
        emb_status = "STABLE"
        if current_embeddings is not None and len(current_embeddings) > 0:
            w_dist, emb_status = self.evaluate_embedding_drift(current_embeddings)

        ph_stat = self.ph_test.current_stat
        concept_drift = ph_stat > self.ph_test.threshold

        summary = (
            f"PSI={price_psi:.3f} ({psi_status}), "
            f"Embedding Wasserstein={w_dist:.3f} ({emb_status}), "
            f"Concept PH={ph_stat:.2f} ({'DRIFT' if concept_drift else 'STABLE'})"
        )

        return DriftReport(
            timestamp=time.time(),
            psi_score=round(price_psi, 4),
            psi_status=psi_status,
            wasserstein_embedding_distance=round(w_dist, 4),
            wasserstein_distance=round(w_dist, 4),
            embedding_drift_status=emb_status,
            page_hinkley_statistic=round(ph_stat, 2),
            page_hinkley_stat=round(ph_stat, 2),
            concept_drift_detected=concept_drift,
            summary=summary,
            feature_psi_breakdown={"base_price": round(price_psi, 4)},
        )
