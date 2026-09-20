"""Catalog controller: internal products and competitor inventory listings."""

from typing import Any, Dict, List

from fastapi import APIRouter, Request

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state

logger = get_logger("api.routes.catalog")
router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/internal", response_model=List[Dict[str, Any]])
async def list_internal_catalog(request: Request):
    """Lists enterprise internal products."""
    state = get_app_state(request)
    return state.internal_raw_list


@router.get("/competitor", response_model=List[Dict[str, Any]])
async def list_competitor_catalog(request: Request):
    """Lists ingested competitor products with status flags."""
    state = get_app_state(request)
    return state.competitor_raw_list
