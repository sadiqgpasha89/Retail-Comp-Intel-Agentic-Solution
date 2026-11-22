"""Model & Feature Registry: tracks versions, thresholds and status.

The ``metrics`` dict is empty until an evaluation run records real values; the registry never
ships made-up quality figures. Versions/status describe the bundled demo models only.
"""

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
                metrics={},  # no offline evaluation recorded for the demo encoder
                parameters={"dimension": 64, "metric": "cosine"},
            ),
            "cross_encoder": ModelArtifact(
                model_name="cross_encoder",
                model_version="v1.4.2",
                model_type="cross_encoder",
                status="PRODUCTION",
                metrics={},
                parameters={"auto_commit_threshold": 0.92, "escalation_threshold": 0.65},
            ),
            "anomaly_detector": ModelArtifact(
                model_name="anomaly_detector",
                model_version="v1.0.1",
                model_type="isolation_forest",
                status="PRODUCTION",
                metrics={},
                parameters={"n_estimators": 100},
            ),
        }

    def get_artifact(self, model_name: str) -> Optional[ModelArtifact]:
        return self._artifacts.get(model_name)

    def list_artifacts(self) -> List[ModelArtifact]:
        return list(self._artifacts.values())
