#!/usr/bin/env python3
"""
Operational script: runs the Golden Benchmark evaluation suite and prints a report.

Usage:
    python scripts/run_golden_eval.py [--benchmark-path PATH]
"""

import argparse
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

    # Perfect oracle decisions for baseline verification
    oracle_decisions = {
        b["competitor_sku"]: {
            "verdict": b["expected_match_type"],
            "target_sku": b["expected_target_sku"],
        }
        for b in benchmarks
    }

    report = runner.evaluate_decisions(oracle_decisions)
    print(json.dumps(report.model_dump(), indent=2))
    print(f"\n✅ Accuracy: {report.accuracy * 100:.1f}% ({report.passed_count}/{report.total_benchmarks})")


if __name__ == "__main__":
    main()
