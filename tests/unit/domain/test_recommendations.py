"""Acceptance scenarios 8 and 9: margin-aware recommendation with enforced floors; approval gate and audit trail."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from retail_intel.domain.audit import AuditLog
from retail_intel.domain.recommendations import (InsufficientInputs, InvalidTransition, NotAuthorized, PolicyBlocked,
                                                 PolicyConfig, PolicyEngine, RecStatus, RecType, Recommendation,
                                                 RecommendationWorkflow, SkuContext, WritesDisabled, estimate_margin_impact)
from retail_intel.domain.store import ObservationStore

pytestmark = pytest.mark.unit
NOW = datetime(2026, 4, 1, tzinfo=timezone.utc)


class FakeRepricer:
    def __init__(self):
        self.calls = []

    def apply(self, rec, key):
        self.calls.append(key)
        return {"applied": True, "price": str(rec.proposed_price)}


def ctx(**kw):
    return SkuContext(**{"internal_sku": "S1", "price": D("100"), "currency": "USD", "cogs": D("60"), "inventory_units": 10, **kw})


def rec(price="95", **kw):
    return Recommendation(**{"recommendation_id": "R1", "tenant_id": "t1", "rec_type": RecType.REVIEW_PRICE, "internal_sku": "S1",
                             "currency": "USD", "current_price": D("100"), "proposed_price": D(price),
                             "rationale": "Competitor 5% lower on 3 matched sources", "evidence_ids": ["obs_1"], **kw})


def flow(**kw):
    store = ObservationStore()
    audit = AuditLog(store)
    return RecommendationWorkflow(audit, PolicyEngine(PolicyConfig(min_margin_pct=D("10"))), store=store,
                                  clock=lambda: NOW, **kw), audit, store


def test_estimate_requires_inputs_and_returns_a_range():
    gap = estimate_margin_impact(current_price=D(100), proposed_price=D(95), unit_cost=None, weekly_units=D(100),
                                 elasticity_low=D(-1), elasticity_expected=D(-1.5), elasticity_high=D(-2))
    assert isinstance(gap, InsufficientInputs) and gap.missing == ["unit_cost"]
    est = estimate_margin_impact(current_price=D(100), proposed_price=D(95), unit_cost=D(60), weekly_units=D(100),
                                 elasticity_low=D(-1), elasticity_expected=D(-2), elasticity_high=D(-3))
    assert est.margin_delta_low <= est.margin_delta_expected <= est.margin_delta_high
    assert any("elasticity" in a.lower() for a in est.assumptions)


@pytest.mark.parametrize("price,code", [("64", "MARGIN_FLOOR"), ("101", None), ("60", "MARGIN_FLOOR"), ("65", "CHANGE_TOO_LARGE")])
def test_policy_floor_and_change_bounds(price, code):
    v = PolicyEngine().check(rec(price), ctx())
    assert (code in [x.code for x in v]) if code else not [x for x in v if x.code in ("MARGIN_FLOOR", "CHANGE_TOO_LARGE")]


def test_policy_map_cogs_unknown_stock_currency():
    codes = lambda r, c: {x.code for x in PolicyEngine().check(r, c)}
    assert "MAP_VIOLATION" in codes(rec("90"), ctx(map_price=D("95")))
    assert "COGS_UNKNOWN" in codes(rec("95"), ctx(cogs=None))
    assert "NO_STOCK_FOR_PROMOTION" in codes(rec(rec_type=RecType.EVALUATE_PROMOTION), ctx(inventory_units=0))
    assert "CURRENCY_MISMATCH" in codes(rec(), ctx(currency="EUR"))
    assert not codes(rec(rec_type=RecType.MONITOR, proposed_price=None), ctx(cogs=None))


def test_full_lifecycle_with_audit_trail_and_dry_run_default():
    wf, audit, _ = flow(integration=FakeRepricer(), writes_enabled=True)
    wf.propose(rec())
    wf.review("R1", "ana", "analyst")
    wf.approve("R1", "pat", "pricing_manager", ctx())
    dry = wf.execute("R1", "pat", "k1")                       # dry_run defaults to True
    assert dry["dry_run"] and wf.get("R1").status == RecStatus.APPROVED and not wf.integration.calls
    live = wf.execute("R1", "pat", "k1", dry_run=False)
    assert live["applied"] and wf.get("R1").status == RecStatus.ACTIONED
    assert wf.execute("R1", "pat", "k1", dry_run=False) == live and wf.integration.calls == ["k1"]   # idempotent
    wf.record_outcome("R1", "pat", {"margin_delta": "120.00"})
    assert wf.get("R1").status == RecStatus.MEASURED
    assert [e.action for e in audit.events("R1")] == ["propose", "review", "approve", "dry_run", "execute", "measure"]
    assert audit.verify()


def test_writes_are_disabled_by_default():
    wf, audit, _ = flow(integration=FakeRepricer())            # integration present but writes_enabled False
    wf.propose(rec()); wf.review("R1", "ana", "analyst"); wf.approve("R1", "pat", "admin", ctx())
    with pytest.raises(WritesDisabled):
        wf.execute("R1", "pat", "k1", dry_run=False)
    assert wf.integration.calls == [] and "write_refused" in [e.action for e in audit.events("R1")]


def test_approval_gates():
    wf, audit, _ = flow()
    wf.propose(rec("40"))
    with pytest.raises(InvalidTransition):
        wf.approve("R1", "pat", "admin", ctx())                # not reviewed yet
    wf.review("R1", "ana", "analyst")
    with pytest.raises(NotAuthorized):
        wf.approve("R1", "ana", "analyst", ctx())              # analysts cannot approve
    with pytest.raises(PolicyBlocked) as e:
        wf.approve("R1", "pat", "pricing_manager", ctx())      # 40 < margin floor
    assert "MARGIN_FLOOR" in str(e.value) and wf.get("R1").status == RecStatus.REVIEWED
    acts = [x.action for x in audit.events("R1")]
    assert "approval_denied" in acts and "approval_blocked" in acts


def test_cannot_execute_unapproved_and_rejection_needs_reason():
    wf, _, _ = flow()
    wf.propose(rec())
    with pytest.raises(InvalidTransition):
        wf.execute("R1", "pat", "k")
    with pytest.raises(Exception):
        wf.reject("R1", "pat", "pricing_manager", "")
    wf.reject("R1", "pat", "pricing_manager", "competitor price is promo-only")
    with pytest.raises(InvalidTransition):
        wf.review("R1", "ana", "analyst")


def test_expiry_and_persistence_across_instances():
    now = [NOW]
    store = ObservationStore()
    wf = RecommendationWorkflow(AuditLog(store), store=store, clock=lambda: now[0])
    wf.propose(rec(expires_at=NOW + timedelta(days=1)))
    wf2 = RecommendationWorkflow(AuditLog(store), store=store, clock=lambda: now[0])
    assert wf2.get("R1").status == RecStatus.PROPOSED          # loaded from the store
    now[0] = NOW + timedelta(days=2)
    assert wf2.expire_due() == ["R1"] and wf2.get("R1").status == RecStatus.EXPIRED


def test_audit_chain_detects_tampering():
    audit = AuditLog()
    for i in range(3):
        audit.record("a", "act", "e", str(i))
    assert audit.verify()
    audit.sink._events[1].details["x"] = "tampered"
    assert not audit.verify()
