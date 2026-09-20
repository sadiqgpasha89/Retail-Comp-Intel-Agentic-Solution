"""Model & Feature Registry: tracks versions, candidate match thresholds, and operational status."""

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelArtifact(BaseModel):
    model_name: str
    model_version: str
    model_type: str  # "bi_encoder", "cross_encoder", "isolation_forest"
    status: str  # "PRODUCTION", "STAGING", "RETIRED"
    created_at: float = Field(default_factory=time.time)
    metrics: Dict[str, float] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ModelRegistry:
    """Enterprise MLOps Model Registry."""
    def __init__(self):
        self._artifacts: Dict[str, ModelArtifact] = {
            "bi_encoder": ModelArtifact(
                model_name="bi_encoder",
                model_version="v2.1.0",
                model_type="bi_encoder",
                status="PRODUCTION",
                metrics={"recall_at_5": 0.94, "p99_latency_ms": 12.4},
                parameters={"dimension": 64, "metric": "cosine"},
            ),
            "cross_encoder": ModelArtifact(
                model_name="cross_encoder",
                model_version="v1.4.2",
                model_type="cross_encoder",
                status="PRODUCTION",
                metrics={"pr_auc": 0.91, "f1_score": 0.89},
                parameters={"auto_commit_threshold": 0.92, "escalation_threshold": 0.65},
            ),
            "anomaly_detector": ModelArtifact(
                model_name="anomaly_detector",
                model_version="v1.0.1",
                model_type="isolation_forest",
                status="PRODUCTION",
                metrics={"contamination": 0.05, "precision": 0.96},
                parameters={"n_estimators": 100},
            ),
        }

    def get_artifact(self, model_name: str) -> Optional[ModelArtifact]:
        return self._artifacts.get(model_name)

    def list_artifacts(self) -> List[ModelArtifact]:
        return list(self._artifacts.values())
