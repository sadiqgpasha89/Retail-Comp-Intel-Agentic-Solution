"""Configuration module for Retail Competitor Intelligence Platform."""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionMode(str, Enum):
    """Supported infrastructure runtime modes."""
    OPEN_STACK = "open_stack"
    GCP = "gcp"


def _resolve_base_dir() -> Path:
    """Resolves project root directory robustly in both installed and dev modes."""
    # Honour explicit env override first (useful in containers)
    env_override = os.environ.get("RETAIL_INTEL_BASE_DIR")
    if env_override:
        return Path(env_override).resolve()
    # Walk up from this file: src/retail_intel/core/config.py → project root
    return Path(__file__).resolve().parent.parent.parent.parent


class AppSettings(BaseSettings):
    """Application-wide settings with environment overrides."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "RetailCompIntelAgentic"
    app_env: str = "development"
    log_level: str = "INFO"
    execution_mode: ExecutionMode = ExecutionMode.OPEN_STACK

    # Network / API
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # CORS — comma-separated list of allowed origins (never use "*" with credentials)
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    # Decision Boundaries (Tri-Tier Hybrid Split)
    auto_commit_threshold: float = 0.92
    agentic_escalation_threshold: float = 0.65
    reject_threshold: float = 0.40

    # Multimodal Weights: alpha*text + beta*vis + gamma*attr
    default_weight_textual: float = 0.45
    default_weight_visual: float = 0.35
    default_weight_attributes: float = 0.20

    # Category-specific multimodal weight calibration
    category_weights: Dict[str, Dict[str, float]] = Field(default_factory=lambda: {
        "apparel": {"alpha": 0.25, "beta": 0.55, "gamma": 0.20},
        "electronics": {"alpha": 0.35, "beta": 0.25, "gamma": 0.40},
        "grocery": {"alpha": 0.40, "beta": 0.20, "gamma": 0.40},
        "hardware": {"alpha": 0.20, "beta": 0.20, "gamma": 0.60},
        "furniture": {"alpha": 0.30, "beta": 0.45, "gamma": 0.25},
    })

    # MLOps Drift Tolerances
    psi_warning_threshold: float = 0.10
    psi_critical_threshold: float = 0.25
    wasserstein_drift_threshold: float = 0.18
    page_hinkley_threshold: float = 50.0

    # LLM & Agentic AI Settings
    gemini_api_key: Optional[str] = None
    vertex_project_id: Optional[str] = None
    vertex_location: str = "us-central1"
    gemini_model: str = "gemini-2.0-flash"
    agent_max_iterations: int = 6
    agent_step_budget: int = 10

    # Storage & Persistence
    database_url: str = "sqlite:///./data/retail_intel.db"
    vector_dimension: int = 64
    redis_url: str = "redis://localhost:6379/0"

    # Local storage directory for file-backed provider
    local_storage_dir: str = "./data/payload_store"

    # GCP Cloud Resource Configuration (Active when execution_mode == GCP)
    gcp_pubsub_topic_ingestion: str = "projects/retail-intel/topics/competitor-raw-ingest"
    gcp_pubsub_topic_alerts: str = "projects/retail-intel/topics/merch-action-alerts"
    gcp_bigquery_dataset: str = "retail_competitive_intelligence"
    gcp_spanner_instance: str = "retail-graph-instance"
    gcp_spanner_database: str = "retail-knowledge-graph"
    gcp_gcs_bucket_payloads: str = "retail-intel-raw-payloads-lake"

    @property
    def base_dir(self) -> Path:
        return _resolve_base_dir()

    @property
    def internal_catalog_path(self) -> Path:
        return self.base_dir / "data" / "internal_catalog.json"

    @property
    def competitor_catalog_path(self) -> Path:
        return self.base_dir / "data" / "competitor_catalog.json"

    @property
    def golden_benchmark_path(self) -> Path:
        return self.base_dir / "data" / "golden_benchmark_set.json"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = AppSettings()
