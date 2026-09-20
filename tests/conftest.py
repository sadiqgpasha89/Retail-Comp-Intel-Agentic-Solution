"""Shared test fixtures for Retail Competitor Intelligence Platform."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from retail_intel.api.main import app, ApplicationState
from retail_intel.core.config import settings
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizationPipeline
from retail_intel.data_engineering.feature_store.feature_store import FeatureStore
from retail_intel.datascience.tier1_rules.deterministic_engine import DeterministicRuleEngine


@pytest.fixture(scope="session")
def base_data_dir():
    return Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="session")
def sample_internal_items(base_data_dir):
    with open(base_data_dir / "internal_catalog.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_competitor_items(base_data_dir):
    with open(base_data_dir / "competitor_catalog.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client
