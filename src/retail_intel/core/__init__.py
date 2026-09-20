"""retail_intel.core package."""
from retail_intel.core.config import settings, ExecutionMode
from retail_intel.core.logging import get_logger, configure_logging, correlation_id_var
from retail_intel.core.exceptions import (
    RetailIntelException, IngestionError, NormalizationError,
    DriftThresholdExceededError, AmbiguousMatchError, PhantomStockDetectedError,
    HoneypotDetectedError, MultimodalClashError, AgentBudgetExceededError,
)

__all__ = [
    "settings", "ExecutionMode",
    "get_logger", "configure_logging", "correlation_id_var",
    "RetailIntelException", "IngestionError", "NormalizationError",
    "DriftThresholdExceededError", "AmbiguousMatchError", "PhantomStockDetectedError",
    "HoneypotDetectedError", "MultimodalClashError", "AgentBudgetExceededError",
]
