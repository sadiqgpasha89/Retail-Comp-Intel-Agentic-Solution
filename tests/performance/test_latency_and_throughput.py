"""Performance SLA & Throughput Benchmark Tests."""

import time
import numpy as np
import pytest
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizationPipeline
from retail_intel.data_engineering.feature_store.feature_store import FeatureStore
from retail_intel.datascience.tier2_ml.cross_encoder import CrossEncoderScorer


@pytest.mark.performance
def test_p99_retrieval_latency_sla(sample_internal_items):
    normalizer = NormalizationPipeline()
    internal_records = [normalizer.normalize_internal_product(x) for x in sample_internal_items]

    feature_store = FeatureStore()
    feature_store.index_internal_catalog(internal_records)

    latencies = []
    test_rec = internal_records[0]

    # Benchmark 100 vector queries
    for _ in range(100):
        t0 = time.time()
        _ = feature_store.find_nearest_candidates(test_rec, top_k=3)
        latencies.append((time.time() - t0) * 1000)

    p99 = float(np.percentile(latencies, 99))
    p50 = float(np.percentile(latencies, 50))

    # Strict SLA Assertion: P99 < 30ms for vector retrieval
    assert p99 < 30.0, f"P99 retrieval latency {p99:.2f}ms exceeds 30ms SLA"
    assert p50 < 10.0, f"P50 retrieval latency {p50:.2f}ms exceeds 10ms SLA"


@pytest.mark.performance
def test_pipeline_throughput_benchmark(sample_internal_items, sample_competitor_items):
    normalizer = NormalizationPipeline()
    internal_records = [normalizer.normalize_internal_product(x) for x in sample_internal_items]
    comp_records = [normalizer.normalize_competitor_payload(x) for x in sample_competitor_items]

    cross_encoder = CrossEncoderScorer()

    # Benchmark 500 candidate pair evaluations
    t0 = time.time()
    iterations = 500
    for i in range(iterations):
        c_rec = comp_records[i % len(comp_records)]
        i_rec = internal_records[i % len(internal_records)]
        _ = cross_encoder.score_pair(c_rec, i_rec, bi_encoder_similarity=0.85)

    elapsed = time.time() - t0
    throughput = iterations / max(0.001, elapsed)

    # Assert throughput > 200 pairs / second
    assert throughput > 200.0, f"Throughput {throughput:.1f} pairs/sec is below 200/sec benchmark"
