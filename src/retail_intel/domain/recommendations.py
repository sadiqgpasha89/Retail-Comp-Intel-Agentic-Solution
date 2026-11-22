"""Recommendation lifecycle, policy enforcement and approval-gated execution (plan sections 2.8 and 3).

proposed -> reviewed -> approved/rejected -> actioned -> measured (or expired).
A match decision is not a price recommendation; a recommendation is not an approved price change. Writes are off by
default; dry-run is the default execution mode.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from retail_intel.domain.audit import AuditLog
from retail_intel.domain.store import ObservationStore


class RecType(str, Enum):
    MONITOR = "MONITOR"
    INVESTIGATE = "INVESTIGATE"
    HOLD_PRICE = "HOLD_PRICE"
    REVIEW_PRICE = "REVIEW_PRICE"
    PROTECT_MARGIN = "PROTECT_MARGIN"
    EVALUATE_PROMOTION = "EVALUATE_PROMOTION"
    SOURCE_EQUIVALENT = "SOURCE_EQUIVALENT"
    ESCALATE_COMPLIANCE = "ESCALATE_COMPLIANCE"


PRICE_ACTIONS = {RecType.REVIEW_PRICE, RecType.PROTECT_MARGIN, RecType.HOLD_PRICE, RecType.EVALUATE_PROMOTION}


class RecStatus(str, Enum):
    PROPOSED = "PROPOSED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIONED = "ACTIONED"
    MEASURED = "MEASURED"
    EXPIRED = "EXPIRED"


TERMINAL = {RecStatus.REJECTED, RecStatus.MEASURED, RecStatus.EXPIRED}
APPROVER_ROLES = {"pricing_manager", "category_manager", "admin"}
REVIEWER_ROLES = APPROVER_ROLES | {"analyst"}


class InsufficientInputs(BaseModel):
    missing: List[str]
    message: str = "A financial estimate needs internal sales, cost and elasticity inputs; none were invented."


class FinancialEstimate(BaseModel):
    horizon: str = "1 week"
    margin_delta_low: Decimal
    margin_delta_expected: Decimal
    margin_delta_high: Decimal
    assumptions: List[str]


def estimate_margin_impact(*, current_price: Optional[Decimal], proposed_price: Optional[Decimal], unit_cost: Optional[Decimal],
                           weekly_units: Optional[Decimal], elasticity_low: Optional[Decimal],
                           elasticity_expected: Optional[Decimal], elasticity_high: Optional[Decimal]
                           ) -> FinancialEstimate | InsufficientInputs:
    """Weekly gross-margin delta for a price change, as a range. Returns InsufficientInputs rather than guessing."""
    inputs = {"current_price": current_price, "proposed_price": proposed_price, "unit_cost": unit_cost,
              "weekly_units": weekly_units, "elasticity_low": elasticity_low,
              "elasticity_expected": elasticity_expected, "elasticity_high": elasticity_high}
    missing = [k for k, v in inputs.items() if v is None]
    if missing:
        return InsufficientInputs(missing=missing)
    assert current_price and proposed_price and unit_cost is not None and weekly_units is not None
    pct = (proposed_price - current_price) / current_price
    base = weekly_units * (current_price - unit_cost)

    def delta(e: Decimal) -> Decimal:
        units = max(Decimal(0), weekly_units * (1 + e * pct))
        return units * (proposed_price - unit_cost) - base

    vals = sorted(delta(e) for e in (elasticity_low, elasticity_expected, elasticity_high))  # type: ignore[arg-type]
    exp = delta(elasticity_expected)  # type: ignore[arg-type]
    q = Decimal("0.01")
    return FinancialEstimate(
        margin_delta_low=vals[0].quantize(q), margin_delta_expected=exp.quantize(q), margin_delta_high=vals[-1].quantize(q),
        assumptions=["Constant price elasticity over the horizon", "Competitor prices held constant (no reaction)",
                     "Unit cost constant; no inventory or supply constraints",
                     f"Elasticity range supplied by caller: {elasticity_low}..{elasticity_high}"])


class SkuContext(BaseModel):
    internal_sku: str
    price: Decimal
    currency: str
    cogs: Optional[Decimal] = None
    inventory_units: Optional[int] = None
    map_price: Optional[Decimal] = None
    price_floor: Optional[Decimal] = None
    price_ceiling: Optional[Decimal] = None
    region: Optional[str] = None


class PolicyConfig(BaseModel):
    min_margin_pct: Decimal = Decimal("10")       # of price; blocks proposals whose margin falls below this
    max_change_pct: Decimal = Decimal("30")
    allowed_regions: Optional[List[str]] = None


class PolicyViolation(BaseModel):
    code: str
    message: str
    blocking: bool = True


class PolicyEngine:
    def __init__(self, config: Optional[PolicyConfig] = None) -> None:
        self.config = config or PolicyConfig()

    def check(self, rec: "Recommendation", ctx: SkuContext) -> List[PolicyViolation]:
        v: List[PolicyViolation] = []
        c = self.config
        if rec.currency != ctx.currency:
            v.append(PolicyViolation(code="CURRENCY_MISMATCH", message=f"Recommendation in {rec.currency}, SKU priced in {ctx.currency}"))
        if c.allowed_regions is not None and rec.region not in c.allowed_regions:
            v.append(PolicyViolation(code="REGION_NOT_ALLOWED", message=f"Region {rec.region} not in allowed regions"))
        if rec.rec_type == RecType.EVALUATE_PROMOTION and ctx.inventory_units == 0:
            v.append(PolicyViolation(code="NO_STOCK_FOR_PROMOTION", message="Cannot promote a SKU with zero inventory"))
        p = rec.proposed_price
        if p is None or rec.rec_type not in PRICE_ACTIONS:
            return v
        if ctx.cogs is None:
            v.append(PolicyViolation(code="COGS_UNKNOWN", message="Cost of goods unknown; margin floor cannot be verified"))
        else:
            floor = ctx.cogs / (1 - c.min_margin_pct / 100)
            if ctx.price_floor is not None:
                floor = max(floor, ctx.price_floor)
            if p < floor:
                v.append(PolicyViolation(code="MARGIN_FLOOR", message=f"Proposed {p} is below floor {floor.quantize(Decimal('0.01'))}"))
        if ctx.price_floor is not None and p < ctx.price_floor:
            v.append(PolicyViolation(code="PRICE_FLOOR", message=f"Proposed {p} is below configured price floor {ctx.price_floor}"))
        if ctx.price_ceiling is not None and p > ctx.price_ceiling:
            v.append(PolicyViolation(code="PRICE_CEILING", message=f"Proposed {p} exceeds ceiling {ctx.price_ceiling}"))
        if ctx.map_price is not None and p < ctx.map_price:
            v.append(PolicyViolation(code="MAP_VIOLATION", message=f"Proposed {p} is below MAP {ctx.map_price}"))
        if ctx.price > 0 and abs(p - ctx.price) / ctx.price * 100 > c.max_change_pct:
            v.append(PolicyViolation(code="CHANGE_TOO_LARGE", message=f"Change exceeds {c.max_change_pct}% bound"))
        return v


class DecisionRecord(BaseModel):
    actor: str
    action: str
    at: datetime
    notes: str = ""


class Recommendation(BaseModel):
    recommendation_id: str
    tenant_id: str
    rec_type: RecType
    internal_sku: str
    competitor_listing_id: Optional[str] = None
    currency: str
    region: Optional[str] = None
    current_price: Optional[Decimal] = None
    proposed_price: Optional[Decimal] = None
    rationale: str
    evidence_ids: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    estimate: Optional[FinancialEstimate] = None
    estimate_gap: Optional[InsufficientInputs] = None
    status: RecStatus = RecStatus.PROPOSED
    owner: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    decisions: List[DecisionRecord] = Field(default_factory=list)
    executions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)   # idempotency_key -> result
    outcome: Optional[Dict[str, Any]] = None


class WorkflowError(Exception):
    pass


class InvalidTransition(WorkflowError):
    pass


class NotAuthorized(WorkflowError):
    pass


class PolicyBlocked(WorkflowError):
    def __init__(self, violations: List[PolicyViolation]):
        super().__init__("; ".join(f"{x.code}: {x.message}" for x in violations))
        self.violations = violations


class WritesDisabled(WorkflowError):
    pass


class WriteIntegration(Protocol):
    """Downstream system adapter (repricer, ERP). Not provided by default; see SADR ADR-007."""
    def apply(self, rec: Recommendation, idempotency_key: str) -> Dict[str, Any]: ...


class RecommendationWorkflow:
    def __init__(self, audit: AuditLog, policy: Optional[PolicyEngine] = None, store: Optional[ObservationStore] = None,
                 integration: Optional[WriteIntegration] = None, writes_enabled: bool = False,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.audit, self.policy, self.store = audit, policy or PolicyEngine(), store
        self.integration, self.writes_enabled, self._clock = integration, writes_enabled, clock
        self._recs: Dict[str, Recommendation] = {}
        self._lock = threading.RLock()

    def _save(self, rec: Recommendation) -> None:
        self._recs[rec.recommendation_id] = rec
        if self.store:
            self.store.save_recommendation(rec.recommendation_id, rec.tenant_id, rec.status.value, rec.model_dump_json())

    def get(self, rec_id: str) -> Recommendation:
        with self._lock:
            if rec_id in self._recs:
                return self._recs[rec_id]
            if self.store and (raw := self.store.load_recommendation(rec_id)):
                rec = Recommendation.model_validate_json(raw)
                self._recs[rec_id] = rec
                return rec
        raise WorkflowError(f"Unknown recommendation {rec_id}")

    def list(self, status: Optional[RecStatus] = None) -> List[Recommendation]:
        with self._lock:
            return [r for r in self._recs.values() if status is None or r.status == status]

    def _move(self, rec: Recommendation, allowed: set, to: RecStatus, actor: str, action: str, notes: str = "") -> None:
        if rec.status not in allowed:
            raise InvalidTransition(f"{rec.recommendation_id}: {rec.status.value} -> {to.value} is not allowed")
        now = self._clock()
        if rec.expires_at and now > rec.expires_at and to != RecStatus.EXPIRED:
            self._expire(rec)
            raise InvalidTransition(f"{rec.recommendation_id} has expired")
        rec.status = to
        rec.decisions.append(DecisionRecord(actor=actor, action=action, at=now, notes=notes))
        self.audit.record(actor, action, "recommendation", rec.recommendation_id,
                          {"to": to.value, "notes": notes}, ts=now)
        self._save(rec)

    def _expire(self, rec: Recommendation) -> None:
        if rec.status not in TERMINAL:
            rec.status = RecStatus.EXPIRED
            rec.decisions.append(DecisionRecord(actor="system", action="expire", at=self._clock()))
            self.audit.record("system", "expire", "recommendation", rec.recommendation_id, {"to": "EXPIRED"})
            self._save(rec)

    def propose(self, rec: Recommendation, actor: str = "system") -> Recommendation:
        with self._lock:
            if rec.recommendation_id in self._recs:
                return self._recs[rec.recommendation_id]       # idempotent re-proposal
            self._save(rec)
            self.audit.record(actor, "propose", "recommendation", rec.recommendation_id,
                              {"type": rec.rec_type.value, "sku": rec.internal_sku, "evidence": rec.evidence_ids})
            return rec

    def review(self, rec_id: str, reviewer: str, role: str, notes: str = "") -> Recommendation:
        with self._lock:
            if role not in REVIEWER_ROLES:
                raise NotAuthorized(f"Role '{role}' cannot review")
            rec = self.get(rec_id)
            self._move(rec, {RecStatus.PROPOSED}, RecStatus.REVIEWED, reviewer, "review", notes)
            rec.owner = rec.owner or reviewer
            self._save(rec)
            return rec

    def approve(self, rec_id: str, approver: str, role: str, ctx: SkuContext, notes: str = "") -> Recommendation:
        with self._lock:
            if role not in APPROVER_ROLES:
                self.audit.record(approver, "approval_denied", "recommendation", rec_id, {"role": role})
                raise NotAuthorized(f"Role '{role}' cannot approve")
            rec = self.get(rec_id)
            if rec.status != RecStatus.REVIEWED:
                raise InvalidTransition(f"{rec_id}: approval requires REVIEWED, found {rec.status.value}")
            violations = [x for x in self.policy.check(rec, ctx) if x.blocking]
            if violations:
                self.audit.record(approver, "approval_blocked", "recommendation", rec_id,
                                  {"violations": [x.model_dump() for x in violations]})
                raise PolicyBlocked(violations)
            self._move(rec, {RecStatus.REVIEWED}, RecStatus.APPROVED, approver, "approve", notes)
            return rec

    def reject(self, rec_id: str, reviewer: str, role: str, reason: str) -> Recommendation:
        with self._lock:
            if role not in REVIEWER_ROLES:
                raise NotAuthorized(f"Role '{role}' cannot reject")
            if not reason:
                raise WorkflowError("A rejection reason is required")
            rec = self.get(rec_id)
            self._move(rec, {RecStatus.PROPOSED, RecStatus.REVIEWED}, RecStatus.REJECTED, reviewer, "reject", reason)
            return rec

    def execute(self, rec_id: str, actor: str, idempotency_key: str, dry_run: bool = True) -> Dict[str, Any]:
        """Dry-run by default. A real write needs writes_enabled, a configured integration and an APPROVED recommendation."""
        with self._lock:
            rec = self.get(rec_id)
            if idempotency_key in rec.executions:
                return rec.executions[idempotency_key]
            if rec.status != RecStatus.APPROVED:
                raise InvalidTransition(f"{rec_id}: execution requires APPROVED, found {rec.status.value}")
            if dry_run:
                result = {"dry_run": True, "would_apply": {"sku": rec.internal_sku, "price": str(rec.proposed_price),
                                                            "currency": rec.currency}}
                self.audit.record(actor, "dry_run", "recommendation", rec_id, result)
                return result                                   # dry runs are not cached against the key
            if not self.writes_enabled or self.integration is None:
                self.audit.record(actor, "write_refused", "recommendation", rec_id, {"reason": "writes disabled"})
                raise WritesDisabled("Downstream writes are disabled or no integration is configured")
            result = {"dry_run": False, **self.integration.apply(rec, idempotency_key)}
            rec.executions[idempotency_key] = result
            self._move(rec, {RecStatus.APPROVED}, RecStatus.ACTIONED, actor, "execute", f"key={idempotency_key}")
            return result

    def record_outcome(self, rec_id: str, actor: str, measured: Dict[str, Any]) -> Recommendation:
        with self._lock:
            rec = self.get(rec_id)
            rec.outcome = measured
            self._move(rec, {RecStatus.ACTIONED}, RecStatus.MEASURED, actor, "measure", str(measured))
            return rec

    def expire_due(self) -> List[str]:
        with self._lock:
            now, out = self._clock(), []
            for rec in list(self._recs.values()):
                if rec.expires_at and now > rec.expires_at and rec.status not in TERMINAL:
                    self._expire(rec)
                    out.append(rec.recommendation_id)
            return out
