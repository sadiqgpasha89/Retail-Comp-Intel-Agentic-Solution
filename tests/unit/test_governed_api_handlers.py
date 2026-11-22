"""Route-handler tests for the governed recommendation lifecycle and governance endpoints.

Handlers are invoked directly (no HTTP layer) against a real ApplicationState, so they run without a
network or test server. HTTP-level coverage lives in tests/integration.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from retail_intel.api.main import ApplicationState
from retail_intel.api.routes import governance as gov
from retail_intel.api.routes import recommendations as recs
from retail_intel.domain.sources import CompetitorSource, SourcePolicy, SourceType

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

INTERNAL = [
    {"sku": "INT-1", "title": "Widget", "brand": "B", "category": "Home", "current_price": 100.0,
     "cost_of_goods": 60.0, "inventory_units": 10, "gtin": "0", "stock_status": "IN_STOCK"},
    {"sku": "INT-NOCOGS", "title": "Gadget", "brand": "B", "category": "Home", "current_price": 50.0,
     "inventory_units": 10, "gtin": "1", "stock_status": "IN_STOCK"},
]


@pytest.fixture()
def request_obj():
    state = ApplicationState()
    state.internal_raw_list = INTERNAL
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(app_state=state))), state


def _action(sku="INT-1", price=70.0, action_type="AUTO_REPRICE_VOLUME_DEFENSE"):
    return recs.MerchandisingAction(
        recommendation_id="REC-0001", action_type=action_type, urgency="HIGH", category="Home",
        internal_sku=sku, internal_title="t", competitor_id="c", competitor_name="C", competitor_sku="C-1",
        internal_price=100.0, competitor_price=price, price_gap_pct=-30.0, category_price_index=1.0, cogs=60.0,
        current_gross_margin_pct=40.0, recommended_price=price, projected_margin_pct=10.0, financial_impact_usd=1.0,
        executive_directive="d", strategic_rationale="r", action_steps=[], guardrails="g")


async def test_registration_is_idempotent_and_has_stable_ids(request_obj):
    _, state = request_obj
    a1, a2 = _action(), _action()
    recs._register(state, [a1])
    recs._register(state, [a2])
    assert a1.workflow_id == a2.workflow_id
    assert len(state.workflow.list()) == 1
    # No volume/elasticity inputs exist in demo data -> an explicit gap, not an invented number
    rec = state.workflow.list()[0]
    assert rec.estimate is None and rec.estimate_gap is not None


async def test_approval_requires_role_and_passes_policy(request_obj):
    req, state = request_obj
    a = _action(price=80.0)
    recs._register(state, [a])
    rid = a.workflow_id
    body = recs.DecisionRequest(notes="ok")
    with pytest.raises(HTTPException) as e:
        await recs.review_recommendation(rid, body, req, x_actor_id="x", x_actor_role="viewer")
    assert e.value.status_code == 403
    await recs.review_recommendation(rid, body, req, x_actor_id="ana", x_actor_role="analyst")
    with pytest.raises(HTTPException) as e:
        await recs.approve_recommendation(rid, body, req, x_actor_id="ana", x_actor_role="analyst")
    assert e.value.status_code == 403
    out = await recs.approve_recommendation(rid, body, req, x_actor_id="pm", x_actor_role="pricing_manager")
    assert out["status"] == "APPROVED"
    assert state.audit_log.verify()


async def test_margin_floor_blocks_approval(request_obj):
    req, state = request_obj
    a = _action(price=61.0)          # 1.6% margin on a 60 cost: below the 10% floor
    recs._register(state, [a])
    body = recs.DecisionRequest()
    await recs.review_recommendation(a.workflow_id, body, req, x_actor_id="ana", x_actor_role="analyst")
    with pytest.raises(HTTPException) as e:
        await recs.approve_recommendation(a.workflow_id, body, req, x_actor_id="pm", x_actor_role="pricing_manager")
    assert e.value.status_code == 422
    assert any(v["code"] == "MARGIN_FLOOR" for v in e.value.detail["violations"])
    assert state.workflow.get(a.workflow_id).status.value == "REVIEWED"


async def test_unknown_cost_blocks_approval(request_obj):
    req, state = request_obj
    a = _action(sku="INT-NOCOGS", price=45.0)
    recs._register(state, [a])
    body = recs.DecisionRequest()
    await recs.review_recommendation(a.workflow_id, body, req, x_actor_id="ana", x_actor_role="analyst")
    with pytest.raises(HTTPException) as e:
        await recs.approve_recommendation(a.workflow_id, body, req, x_actor_id="pm", x_actor_role="pricing_manager")
    assert any(v["code"] == "COGS_UNKNOWN" for v in e.value.detail["violations"])


async def test_execute_is_dry_run_and_real_writes_are_refused(request_obj):
    req, state = request_obj
    a = _action(price=80.0)
    recs._register(state, [a])
    body = recs.DecisionRequest()
    await recs.review_recommendation(a.workflow_id, body, req, x_actor_id="ana", x_actor_role="analyst")
    await recs.approve_recommendation(a.workflow_id, body, req, x_actor_id="pm", x_actor_role="pricing_manager")
    dry = await recs.execute_recommendation(
        a.workflow_id, recs.ExecuteRequest(idempotency_key="key-12345678"), req, x_actor_id="pm", x_actor_role=None)
    assert dry["dry_run"] is True
    with pytest.raises(HTTPException) as e:
        await recs.execute_recommendation(
            a.workflow_id, recs.ExecuteRequest(idempotency_key="key-87654321", dry_run=False), req,
            x_actor_id="pm", x_actor_role=None)
    assert e.value.status_code == 409
    assert state.workflow.get(a.workflow_id).status.value == "APPROVED"


async def test_unknown_recommendation_is_404(request_obj):
    req, _ = request_obj
    with pytest.raises(HTTPException) as e:
        await recs.review_recommendation("nope", recs.DecisionRequest(), req, x_actor_id="a", x_actor_role="analyst")
    assert e.value.status_code == 404


class _Body:
    def __init__(self, req, payload: bytes):
        self.app, self._p = req.app, payload

    async def body(self):
        return self._p


CSV = (b"competitor_sku,title,price,currency,availability\n"
       b"C-1,Widget,19.99,USD,in stock\n"
       b"C-2,Broken,-5,USD,in stock\n")


async def test_import_requires_a_permitted_source_and_reports_rejections(request_obj):
    req, state = request_obj
    src = CompetitorSource(source_id="s1", competitor_id="c1", merchant="M", country="US", currency="USD",
                           source_type=SourceType.MANUAL_UPLOAD)           # permission NOT established
    state.source_registry.upsert(src)
    with pytest.raises(HTTPException) as e:
        await gov.import_listing_file(_Body(req, CSV), source_id="s1", fmt="csv")
    assert e.value.status_code == 403

    src.policy = SourcePolicy(permitted=True, basis="customer-supplied export, contract 2026-01")
    state.source_registry.upsert(src)
    out = await gov.import_listing_file(_Body(req, CSV), source_id="s1", fmt="csv")
    assert out.rows_total == 2 and len(out.rejected) == 1 and out.observations_stored >= 1

    again = await gov.import_listing_file(_Body(req, CSV), source_id="s1", fmt="csv")
    assert again.observations_stored == 0 and again.observations_duplicate >= 1     # idempotent re-import

    hist = await gov.observation_history(req, kind="price", listing_id="C-1", competitor_id=None, region=None,
                                         as_of=None, include_quarantined=False)
    assert len(hist) == 1
    # the raw upload is retained as content-addressed evidence and referenced from provenance
    uri = hist[0]["provenance"]["evidence_uri"]
    assert uri.startswith("evidence://sha256/")
    assert state.observations.get_evidence(uri.rsplit("/", 1)[1]) == CSV
    assert (await gov.verify_audit(req))["intact"] is True


async def test_unknown_source_is_404(request_obj):
    req, _ = request_obj
    with pytest.raises(HTTPException) as e:
        await gov.import_listing_file(_Body(req, b"x"), source_id="missing", fmt="csv")
    assert e.value.status_code == 404
