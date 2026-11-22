#!/usr/bin/env python3
"""
Operational script: scores the live pipeline against the Golden Benchmark set and prints a report.

No oracle decisions are used; the exit code is non-zero when any benchmark case fails.

Usage:
    python scripts/run_golden_eval.py [--benchmark-path PATH]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure src/ is on the path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from retail_intel.llmops.golden_eval import GoldenBenchmarkRunner


def main():
    parser = argparse.ArgumentParser(description="Run Golden Benchmark Evaluation")
    parser.add_argument(
        "--benchmark-path",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "golden_benchmark_set.json",
    )
    args = parser.parse_args()

    runner = GoldenBenchmarkRunner(benchmark_path=args.benchmark_path)
    benchmarks = runner.load_benchmarks()
    if not benchmarks:
        print(f"[ERROR] No benchmarks found at: {args.benchmark_path}")
        sys.exit(1)

    print(f"Loaded {len(benchmarks)} benchmark cases.\n")

    report = asyncio.run(_run_live(runner, benchmarks))
    print(json.dumps(report.model_dump(), indent=2))
    print(f"\nAccuracy (live pipeline, demo data): {report.accuracy * 100:.1f}% "
          f"({report.passed_count}/{report.total_benchmarks})")
    for row in report.detailed_results:
        if not row["passed"]:
            print(f"  MISS {row['competitor_sku']}: expected {row['expected']} -> "
                  f"{row['expected_target']}, got {row['actual']} -> {row['actual_target']}")
    sys.exit(0 if report.failed_count == 0 else 2)


async def _run_live(runner, benchmarks):
    """Run each benchmark SKU through the real analysis path (no oracle decisions)."""
    from types import SimpleNamespace
    from fastapi import HTTPException
    from retail_intel.api.main import lifespan
    from retail_intel.api.routes.intelligence import analyze_competitor_sku
    from retail_intel.api.schemas import IntelligenceRequest

    app = SimpleNamespace(state=SimpleNamespace())
    decisions = {}
    async with lifespan(app):
        request = SimpleNamespace(app=app)
        for b in benchmarks:
            try:
                res = await analyze_competitor_sku(
                    IntelligenceRequest(competitor_sku=b["competitor_sku"]), request
                )
            except HTTPException:
                continue
            decisions[b["competitor_sku"]] = {
                "verdict": res.get("verdict"),
                "target_sku": res.get("target_internal_sku"),
            }
    return runner.evaluate_decisions(decisions)


if __name__ == "__main__":
    main()
