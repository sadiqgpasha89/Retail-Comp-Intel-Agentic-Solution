"""Unit tests for Tier 1 Deterministic Rule Engine."""

import pytest
from retail_intel.datascience.tier1_rules.deterministic_engine import DeterministicRuleEngine
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord


@pytest.fixture
def sample_records():
    r1 = NormalizedProductRecord(
        source_type="internal",
        source_id="ENTERPRISE",
        sku="INT-EL-001",
        gtin_normalized="000084008050123",
        gtin_valid=True,
        title_clean="AuraWave Headphones",
        brand_clean="AuraWave",
        gpc_category_code="50192700",
        gpc_category_name="Headphones",
        base_price=349.99,
        effective_price=299.99,
        unit_price=299.99,
        unit_measure_standard="count",
        pack_size=1,
        stock_status="IN_STOCK",
        fulfillment_latency_days=1,
        image_url="",
        pdp_url="",
    )
    return [r1]


@pytest.mark.unit
def test_deterministic_gtin_match(sample_records):
    engine = DeterministicRuleEngine(sample_records)
    comp_rec = NormalizedProductRecord(
        source_type="competitor",
        source_id="COMP-A",
        sku="APX-01",
        gtin_normalized="000084008050123",
        gtin_valid=True,
        title_clean="AuraWave Pro Headphones",
        brand_clean="AuraWave",
        gpc_category_code="50192700",
        gpc_category_name="Headphones",
        base_price=289.99,
        effective_price=289.99,
        unit_price=289.99,
        unit_measure_standard="count",
        pack_size=1,
        stock_status="IN_STOCK",
        fulfillment_latency_days=2,
        image_url="",
        pdp_url="",
    )

    res = engine.evaluate(comp_rec)
    assert res.is_resolved is True
    assert res.verdict == "EXACT_MATCH"
    assert res.internal_sku == "INT-EL-001"
    assert res.confidence >= 0.95


@pytest.mark.unit
def test_deterministic_honeypot_trap():
    engine = DeterministicRuleEngine([])
    honeypot_rec = NormalizedProductRecord(
        source_type="competitor",
        source_id="COMP-B",
        sku="HONEY-01",
        gtin_normalized=None,
        gtin_valid=False,
        title_clean="Honeypot Trap Product",
        brand_clean="TrapBrand",
        gpc_category_code="99999999",
        gpc_category_name="General",
        base_price=10.0,
        effective_price=10.0,
        unit_price=10.0,
        unit_measure_standard="count",
        pack_size=1,
        stock_status="IN_STOCK",
        fulfillment_latency_days=1,
        image_url="",
        pdp_url="",
        raw_payload_ref={"is_honeypot": True},
    )
    res = engine.evaluate(honeypot_rec)
    assert res.is_resolved is True
    assert res.verdict == "HONEYPOT_TRAP"
