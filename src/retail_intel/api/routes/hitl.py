"""HITL controller: review queue and analyst decision submissions."""

from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state
from retail_intel.hitl.review_queue import HITLTask, HITLDecision

logger = get_logger("api.routes.hitl")
router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


class HITLResolveRequest(BaseModel):
    decision: str = "APPROVE"
    notes: Optional[str] = ""
    override_target_sku: Optional[str] = None


@router.get("/queue", response_model=List[HITLTask])
async def get_hitl_queue(request: Request):
    """Returns pending ambiguous SKU matches requiring human merchant review."""
    state = get_app_state(request)
    # Only real escalations appear here (Tier-3 results that need a human). No demo tasks are injected.
    return state.hitl_queue.get_pending_tasks()


@router.post("/decision", response_model=HITLTask)
async def submit_hitl_decision(decision: HITLDecision, request: Request):
    """Submits analyst approval, rejection, or manual override."""
    state = get_app_state(request)
    task = state.hitl_queue.submit_decision(decision)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{decision.task_id}' not found")
    # Feed into Page-Hinkley concept drift test
    state.drift_radar.record_match_feedback(is_correct=(decision.decision in ["APPROVE", "CONFIRM"]))
    return task


@router.post("/resolve/{task_id}")
async def resolve_hitl_task(task_id: str, req: HITLResolveRequest, request: Request):
    """Convenience endpoint resolving HITL task by task_id in path."""
    state = get_app_state(request)
    decision = HITLDecision(
        task_id=task_id,
        decision=req.decision,
        analyst_notes=req.notes or "Resolved via dashboard",
        override_target_sku=req.override_target_sku,
    )
    task = state.hitl_queue.submit_decision(decision)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    state.drift_radar.record_match_feedback(is_correct=(req.decision in ["APPROVE", "CONFIRM"]))
    return task
