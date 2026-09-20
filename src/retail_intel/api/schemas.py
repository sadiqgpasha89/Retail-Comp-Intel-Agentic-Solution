"""Pydantic request/response schemas for the Retail Competitor Intelligence API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app_name: str
    execution_mode: str
    internal_catalog_size: int
    competitor_catalog_size: int
    vector_dimension: int


class IntelligenceRequest(BaseModel):
    competitor_sku: str = Field(..., description="Competitor SKU identifier to resolve")
    top_k_candidates: int = Field(default=5, ge=1, le=20)
    force_agentic: bool = Field(default=False, description="Override tri-tier split and force agentic escalation")


class IntelligenceResponse(BaseModel):
    competitor_sku: str
    target_internal_sku: Optional[str]
    verdict: str
    confidence: float
    effective_competitor_price: float
    normalized_unit_price: float
    reasoning_summary: str
    recommended_action: str
    gross_margin_protected_usd: float
    total_steps_executed: int
    plan_optimality_ratio: float


class BatchIntelligenceRequest(BaseModel):
    competitor_skus: List[str] = Field(..., min_length=1, max_length=100)
    top_k_candidates: int = Field(default=5, ge=1, le=20)
