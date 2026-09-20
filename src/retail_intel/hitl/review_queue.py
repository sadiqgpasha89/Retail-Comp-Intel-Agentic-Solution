"""HITL (Human-in-the-Loop) Review Queue: ambiguity escalation and analyst decision capture."""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger

logger = get_logger("hitl.review_queue")


class HITLTaskStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MANUALLY_OVERRIDDEN = "MANUALLY_OVERRIDDEN"


class HITLTask(BaseModel):
    task_id: str
    competitor_sku: str
    internal_sku_candidate: str
    tau_score: float
    escalation_reason: str
    created_at: float
    status: HITLTaskStatus = HITLTaskStatus.PENDING
    analyst_decision: Optional[str] = None
    reviewed_at: Optional[float] = None
    override_sku: Optional[str] = None
    agentic_evidence: Dict[str, Any] = Field(default_factory=dict)


class HITLDecision(BaseModel):
    task_id: str
    decision: str  # "APPROVE", "REJECT", "OVERRIDE"
    analyst_notes: str = ""
    override_target_sku: Optional[str] = None


class HITLReviewQueue:
    """Enterprise Human-in-the-Loop queue for ambiguous SKU match escalations."""

    def __init__(self):
        self._tasks: Dict[str, HITLTask] = {}
        self.approved_count: int = 0
        self.rejected_count: int = 0
        self.override_count: int = 0

    def enqueue_task(
        self,
        competitor_sku: str,
        internal_sku_candidate: str,
        tau_score: float,
        escalation_reason: str,
        agentic_evidence: Optional[Dict[str, Any]] = None,
    ) -> HITLTask:
        """Creates and enqueues a new ambiguous SKU match for human review."""
        # uuid4 is globally unique — eliminates the timestamp+length collision risk
        task_id = f"hitl_{uuid.uuid4().hex}"
        task = HITLTask(
            task_id=task_id,
            competitor_sku=competitor_sku,
            internal_sku_candidate=internal_sku_candidate,
            tau_score=tau_score,
            escalation_reason=escalation_reason,
            created_at=time.time(),
            agentic_evidence=agentic_evidence or {},
        )
        self._tasks[task_id] = task
        logger.info(
            "Task queued for HITL review",
            task_id=task_id,
            sku=competitor_sku,
            tau=tau_score,
        )
        return task

    def get_pending_tasks(self) -> List[HITLTask]:
        return [t for t in self._tasks.values() if t.status == HITLTaskStatus.PENDING]

    def get_task(self, task_id: str) -> Optional[HITLTask]:
        return self._tasks.get(task_id)

    def submit_decision(self, decision: HITLDecision) -> Optional[HITLTask]:
        """Records analyst decision and updates task status."""
        task = self._tasks.get(decision.task_id)
        if not task:
            logger.warning("HITL decision submitted for unknown task", task_id=decision.task_id)
            return None

        task.reviewed_at = time.time()
        task.analyst_decision = decision.decision
        task.override_sku = decision.override_target_sku

        if decision.decision == "APPROVE":
            task.status = HITLTaskStatus.APPROVED
            self.approved_count += 1
        elif decision.decision == "REJECT":
            task.status = HITLTaskStatus.REJECTED
            self.rejected_count += 1
        elif decision.decision == "OVERRIDE":
            task.status = HITLTaskStatus.MANUALLY_OVERRIDDEN
            self.override_count += 1
        else:
            logger.warning("Unknown HITL decision value", decision=decision.decision)

        logger.info(
            "HITL decision recorded",
            task_id=task.task_id,
            status=task.status.value,
        )
        return task

    def get_queue_stats(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self._tasks),
            "pending": len(self.get_pending_tasks()),
            "approved": self.approved_count,
            "rejected": self.rejected_count,
            "manually_overridden": self.override_count,
        }
