"""Knowledge Graph controller: export visual property graph subgraph."""

from typing import Any, Dict

from fastapi import APIRouter, Request

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state

logger = get_logger("api.routes.graph")
router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("/subgraph")
async def get_graph_visualization(request: Request):
    """Returns nodes and edges format for interactive graph rendering."""
    state = get_app_state(request)
    return state.tools.knowledge_graph.export_subgraph_for_ui()
