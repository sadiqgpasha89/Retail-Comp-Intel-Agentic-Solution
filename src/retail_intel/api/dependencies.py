"""FastAPI dependency injection — replaces unsafe global app_state singleton pattern."""

from typing import TYPE_CHECKING
from fastapi import Request

if TYPE_CHECKING:
    from retail_intel.api.main import ApplicationState


def get_app_state(request: Request) -> "ApplicationState":
    """
    FastAPI dependency that retrieves the ApplicationState from request.app.state.
    This is the correct multi-worker-safe approach — each request gets the state
    from the app instance that handled it, not from a module-level global.
    """
    return request.app.state.app_state
