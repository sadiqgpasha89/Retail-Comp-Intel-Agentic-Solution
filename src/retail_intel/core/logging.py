"""Structured logging setup with correlation-ID context binding."""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog

# Per-request correlation ID stored in a ContextVar (async-safe, no threading issues)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def _inject_correlation_id(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """structlog processor: injects the current request correlation ID into every log record."""
    cid = correlation_id_var.get(None)
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configures structured JSON logging with timestamps, context bindings, and correlation ID."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    use_json = log_level.upper() != "DEBUG"

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_correlation_id,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if use_json else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Returns a structured logger bound to the provided component name."""
    return structlog.get_logger(name)
