"""Five-plane metrics aggregator.

Honesty contract: every value returned here is derived from analyses recorded by this
process (counters, observed latencies) or from the live drift audit. A metric that has
no measurement behind it is **omitted (None)** rather than filled with a plausible
constant. Offline model-quality figures (recall@k, PR-AUC, RAG faithfulness, ...) are
produced by evaluation runs, not by this in-process counter, so they are not reported
here; see ``docs/CAPABILITY_MATRIX.md`` and ``scripts/run_golden_eval.py``.

Counters are per-process and reset on restart. Suitable for a single worker; use
Prometheus/OpenTelemetry for multi-worker aggregation (backlog B-05).
"""

import math
from typing import List, Optional

from pydantic import BaseModel

from retail_intel.core.logging import get_logger

logger = get_logger("metrics.engine")


class BusinessMetrics(BaseModel):
    total_competitor_skus_processed: Optional[int] = None
    exact_match_rate: Optional[float] = None
    private_label_detection_rate: Optional[float] = None
    honeypot_interception_rate: Optional[float] = None
    phantom_stock_isolation_rate: Optional[float] = None
    # Sum of per-recommendation *estimates* produced by the strategy layer on demo data.
    gross_margin_protected_usd: Optional[float] = None
    repricing_actions_triggered: Optional[int] = None


class AgenticMetrics(BaseModel):
    total_agentic_escalations: Optional[int] = None
    plan_optimality_ratio_avg: Optional[float] = None
    plan_optimality_ratio: Optional[float] = None
    tool_success_rate: Optional[float] = None
    reflection_correction_rate: Optional[float] = None
    hitl_escalation_rate: Optional[float] = None


class RAGQualityMetrics(BaseModel):
    """Intentionally empty: groundedness is scored per answer by ``llmops.guardrails`` and
    by offline evals; no aggregate is tracked in-process."""
    faithfulness_score_avg: Optional[float] = None
    hallucination_rate_avg: Optional[float] = None


class MLSystemMetrics(BaseModel):
    psi_distribution_score: Optional[float] = None
    wasserstein_embedding_distance: Optional[float] = None


class InfrastructureMetrics(BaseModel):
    active_catalog_size: Optional[int] = None
    normalized_record_count: Optional[int] = None
    vector_index_size: Optional[int] = None
    stream_dlq_depth: Optional[int] = None
    # Observed over the analyses recorded since process start / last reset.
    end_to_end_latency_p99_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None
    latency_sample_count: Optional[int] = None


class Comprehensive5PlaneMetrics(BaseModel):
    business: BusinessMetrics
    agentic: AgenticMetrics
    rag_quality: RAGQualityMetrics
    ml_system: MLSystemMetrics
    infrastructure: InfrastructureMetrics
    system_plane: Optional[InfrastructureMetrics] = None
    rag: Optional[RAGQualityMetrics] = None
    ml: Optional[MLSystemMetrics] = None
    data_provenance: str = (
        "In-process counters over analyses run since startup on demo/synthetic data. "
        "Omitted fields are not measured."
    )


def _p99(values: List[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(0.99 * len(ordered)) - 1))
    return round(ordered[idx], 2)


class MetricsEngine:
    """Aggregates in-process counters into the five observability planes."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.total_processed = 0
        self.exact_matches = 0
        self.private_labels = 0
        self.honeypots = 0
        self.phantoms = 0
        self.agentic_escalations = 0
        self.plan_optimality_sum = 0.0
        self.plan_optimality_n = 0
        self.repricing_actions = 0
        self.gross_margin_protected = 0.0
        self.hitl_escalations = 0
        self.tool_success_count = 0
        self.tool_error_count = 0
        self.reflection_corrections = 0
        self.latencies_ms: List[float] = []

    def record_analysis(
        self,
        verdict: str,
        is_honeypot: bool = False,
        is_phantom: bool = False,
        plan_optimality: Optional[float] = None,
        recommended_action: str = "",
        gross_margin_protected: float = 0.0,
        was_agentic: bool = False,
        was_hitl_escalated: bool = False,
        tool_success: int = 0,
        tool_errors: int = 0,
        reflection_applied: bool = False,
        duration_ms: Optional[float] = None,
    ) -> None:
        self.total_processed += 1
        if verdict == "EXACT_MATCH":
            self.exact_matches += 1
        elif verdict == "EQUIVALENT_PRIVATE_LABEL":
            self.private_labels += 1
        if is_honeypot or verdict == "HONEYPOT_TRAP":
            self.honeypots += 1
        if is_phantom or verdict == "UNFULFILLED_PHANTOM":
            self.phantoms += 1
        if was_agentic:
            self.agentic_escalations += 1
        if plan_optimality is not None:
            self.plan_optimality_sum += plan_optimality
            self.plan_optimality_n += 1
        if recommended_action == "AUTO_REPRICE":
            self.repricing_actions += 1
        self.gross_margin_protected += gross_margin_protected
        if was_hitl_escalated:
            self.hitl_escalations += 1
        self.tool_success_count += tool_success
        self.tool_error_count += tool_errors
        if reflection_applied:
            self.reflection_corrections += 1
        if duration_ms is not None:
            self.latencies_ms.append(float(duration_ms))
            if len(self.latencies_ms) > 5000:  # bound memory
                del self.latencies_ms[: len(self.latencies_ms) - 5000]

    def compute_metrics(
        self,
        psi_score: Optional[float] = None,
        wasserstein_dist: Optional[float] = None,
        active_catalog_size: Optional[int] = None,
        mapped_count: Optional[int] = None,
        dlq_depth: Optional[int] = None,
    ) -> Comprehensive5PlaneMetrics:
        n = self.total_processed
        has = n > 0
        total_tools = self.tool_success_count + self.tool_error_count
        p99 = _p99(self.latencies_ms)

        infra = InfrastructureMetrics(
            active_catalog_size=active_catalog_size,
            normalized_record_count=mapped_count,
            vector_index_size=mapped_count,
            stream_dlq_depth=dlq_depth,
            end_to_end_latency_p99_ms=p99,
            p99_latency_ms=p99,
            latency_sample_count=len(self.latencies_ms) or None,
        )
        biz = BusinessMetrics(
            total_competitor_skus_processed=n if has else None,
            exact_match_rate=round(self.exact_matches / n, 4) if has else None,
            private_label_detection_rate=round(self.private_labels / n, 4) if has else None,
            honeypot_interception_rate=round(self.honeypots / n, 4) if has else None,
            phantom_stock_isolation_rate=round(self.phantoms / n, 4) if has else None,
            gross_margin_protected_usd=round(self.gross_margin_protected, 2) if has else None,
            repricing_actions_triggered=self.repricing_actions if has else None,
        )
        po = (
            round(self.plan_optimality_sum / self.plan_optimality_n, 4)
            if self.plan_optimality_n
            else None
        )
        agent = AgenticMetrics(
            total_agentic_escalations=self.agentic_escalations if has else None,
            plan_optimality_ratio_avg=po,
            plan_optimality_ratio=po,
            tool_success_rate=round(self.tool_success_count / total_tools, 4) if total_tools else None,
            reflection_correction_rate=(
                round(self.reflection_corrections / self.agentic_escalations, 4)
                if self.agentic_escalations
                else None
            ),
            hitl_escalation_rate=round(self.hitl_escalations / n, 4) if has else None,
        )
        rag_q = RAGQualityMetrics()
        ml_s = MLSystemMetrics(
            psi_distribution_score=round(psi_score, 4) if psi_score is not None else None,
            wasserstein_embedding_distance=(
                round(wasserstein_dist, 4) if wasserstein_dist is not None else None
            ),
        )
        return Comprehensive5PlaneMetrics(
            business=biz,
            agentic=agent,
            rag_quality=rag_q,
            ml_system=ml_s,
            infrastructure=infra,
            system_plane=infra,
            rag=rag_q,
            ml=ml_s,
        )
