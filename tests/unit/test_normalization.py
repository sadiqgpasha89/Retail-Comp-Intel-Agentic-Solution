"""Unit tests for Normalization Pipeline (GTIN, units, GPC ontology)."""

import pytest
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizationPipeline, NormalizedProductRecord
from retail_intel.data_engineering.ingestion.ingestion_pipeline import IngestionPayload


@pytest.mark.unit
def test_gtin_validation_valid():
    norm = NormalizationPipeline()
    # Valid GTIN-13 with check digit 8
    standardized, is_valid = norm.validate_and_normalize_gtin("1234567890128")
    assert is_valid is True
    assert standardized == "01234567890128"


@pytest.mark.unit
def test_gtin_validation_invalid():
    norm = NormalizationPipeline()
    # Invalid GTIN-13 check digit (expected 8, got 3)
    _, is_valid = norm.validate_and_normalize_gtin("1234567890123")
    assert is_valid is False


@pytest.mark.unit
def test_gpc_category_alignment():
    norm = NormalizationPipeline()
    code, name = norm.align_gpc_category("Electronics > Over-Ear", "AuraWave Wireless Headphones")
    assert code == "50192700"
    assert "Headphones" in name


@pytest.mark.unit
def test_competitor_payload_normalization():
    norm = NormalizationPipeline()
    payload = IngestionPayload(
        competitor_id="COMP-A",
        competitor_name="ApexRetail",
        competitor_sku="APX-TEST-01",
        gtin="1234567890128",
        title="Test Wireless Headphones 40h Battery",
        brand="AuraWave",
        raw_category="Electronics > Audio",
        scraped_base_price=299.99,
        final_effective_price=279.99,
        pack_size=1,
        pdp_url="https://example.com/pdp",
    )
    rec: NormalizedProductRecord = norm.normalize_competitor_payload(payload)
    assert rec.sku == "APX-TEST-01"
    assert rec.gtin_valid is True
    assert rec.effective_price == 279.99
    assert rec.unit_price == 279.99
    assert rec.gpc_category_code == "50192700"
