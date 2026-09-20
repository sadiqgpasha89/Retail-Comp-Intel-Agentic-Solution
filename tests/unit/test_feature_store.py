"""Unit tests for Feature Store and Multimodal Vector Generation."""

import pytest
import numpy as np
from retail_intel.data_engineering.feature_store.feature_store import FeatureStore
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord


@pytest.fixture
def sample_normalized_record():
    return NormalizedProductRecord(
        source_type="internal",
        source_id="ENTERPRISE",
        sku="INT-HOME-201",
        gtin_normalized=None,
        gtin_valid=False,
        title_clean="ErgoSpine Executive Mesh Office Chair",
        brand_clean="ErgoSpine",
        gpc_category_code="56112102",
        gpc_category_name="Furniture - Ergonomic Task Seating",
        base_price=499.0,
        effective_price=429.0,
        unit_price=429.0,
        unit_measure_standard="count",
        pack_size=1,
        stock_status="IN_STOCK",
        fulfillment_latency_days=1,
        image_url="/chair.jpg",
        pdp_url="",
        normalized_attributes={"material": "Mesh", "weight_capacity_lbs": 300},
    )


@pytest.mark.unit
def test_multimodal_vector_generation(sample_normalized_record):
    store = FeatureStore()
    mv = store.compute_multimodal_vector(sample_normalized_record)

    assert mv.sku == "INT-HOME-201"
    assert mv.dimension == 64
    assert len(mv.embedding) == 64
    # Check normalized unit norm
    norm = np.linalg.norm(np.array(mv.embedding))
    assert pytest.approx(norm, rel=1e-3) == 1.0


@pytest.mark.unit
def test_vector_indexing_and_candidate_search(sample_normalized_record):
    store = FeatureStore()
    count = store.index_internal_catalog([sample_normalized_record])
    assert count == 1

    candidates = store.find_nearest_candidates(sample_normalized_record, top_k=1)
    assert len(candidates) == 1
    sku, score, rec = candidates[0]
    assert sku == "INT-HOME-201"
    assert score >= 0.99  # Self-similarity should be ~1.0
