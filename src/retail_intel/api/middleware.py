"""FastAPI Middleware: Correlation ID injection and CORS configuration."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from retail_intel.core.logging import correlation_id_var, get_logger

logger = get_logger("api.middleware")

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique correlation ID to every inbound request.
    - Reads X-Correlation-ID from request headers if provided by upstream gateway.
    - Otherwise generates a new uuid4.
    - Stores in the async ContextVar so all log lines in the same request share it.
    - Echoes the correlation ID back in the response header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or uuid.uuid4().hex
        # Bind to ContextVar — this is async-safe and propagates into all structlog calls
        token = correlation_id_var.set(correlation_id)
        try:
            t_start = time.perf_counter()
            response: Response = await call_next(request)
            latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=latency_ms,
            )
            return response
        finally:
            correlation_id_var.reset(token)
