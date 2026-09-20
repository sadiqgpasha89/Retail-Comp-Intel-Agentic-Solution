"""Golden Benchmark Set evaluation runner across challenge classes."""

import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from retail_intel.core.config import settings
from retail_intel.core.logging import get_logger

logger = get_logger("llmops.golden_eval")


class BenchmarkRunReport(BaseModel):
    total_benchmarks: int
    passed_count: int
    failed_count: int
    accuracy: float
    per_class_accuracy: Dict[str, float] = Field(default_factory=dict)
    detailed_results: List[Dict[str, Any]] = Field(default_factory=list)


class GoldenBenchmarkRunner:
    """Evaluates agent and ML equivalence decisions against the ground-truth benchmark suite."""
    def __init__(self, benchmark_path: Path | None = None):
        self.benchmark_path = benchmark_path or settings.golden_benchmark_path

    def load_benchmarks(self) -> List[Dict[str, Any]]:
        if not self.benchmark_path.exists():
            return []
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate_decisions(self, live_decisions: Dict[str, Dict[str, Any]]) -> BenchmarkRunReport:
        benchmarks = self.load_benchmarks()
        passed = 0
        per_class_totals: Dict[str, int] = {}
        per_class_passes: Dict[str, int] = {}
        detailed: List[Dict[str, Any]] = []

        for b in benchmarks:
            comp_sku = b["competitor_sku"]
            c_class = b.get("challenge_class", "GENERAL")
            per_class_totals[c_class] = per_class_totals.get(c_class, 0) + 1

            decision = live_decisions.get(comp_sku)
            is_pass = False
            if decision:
                actual_match_type = decision.get("verdict") or decision.get("match_type")
                actual_target = decision.get("target_sku") or decision.get("internal_sku")
                expected_type = b["expected_match_type"]
                expected_target = b["expected_target_sku"]

                type_match = actual_match_type == expected_type
                target_match = (expected_target is None and actual_target is None) or (actual_target == expected_target)

                if type_match and target_match:
                    is_pass = True

            if is_pass:
                passed += 1
                per_class_passes[c_class] = per_class_passes.get(c_class, 0) + 1

            detailed.append({
                "benchmark_id": b["benchmark_id"],
                "competitor_sku": comp_sku,
                "challenge_class": c_class,
                "expected": b["expected_match_type"],
                "actual": decision.get("verdict") if decision else "MISSING",
                "passed": is_pass,
            })

        class_acc = {
            cls_name: round(per_class_passes.get(cls_name, 0) / count, 4)
            for cls_name, count in per_class_totals.items()
        }

        total = len(benchmarks)
        accuracy = round(passed / total, 4) if total > 0 else 1.0

        return BenchmarkRunReport(
            total_benchmarks=total,
            passed_count=passed,
            failed_count=total - passed,
            accuracy=accuracy,
            per_class_accuracy=class_acc,
            detailed_results=detailed,
        )


if __name__ == "__main__":
    runner = GoldenBenchmarkRunner()
    print("Golden Benchmark items loaded:", len(runner.load_benchmarks()))
