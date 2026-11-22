"""Acceptance scenario 6: unknown, unavailable and long-lead-time stay distinct; phantom stock is only a hypothesis."""
from datetime import datetime, timedelta, timezone

import pytest

from retail_intel.domain.availability import (AvailabilitySample, AvailabilityState, ChangeKind, classify_availability,
                                               detect_availability_change, phantom_inventory_hypothesis)

pytestmark = pytest.mark.unit
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_unknown_is_not_out_of_stock():
    for raw in (None, "", "weird status"):
        assert classify_availability(raw).state == AvailabilityState.UNKNOWN
    assert classify_availability("Sold out").state == AvailabilityState.OUT_OF_STOCK


def test_long_lead_time_is_a_flag_not_a_state():
    a = classify_availability("in stock", 30, 45)
    assert a.state == AvailabilityState.IN_STOCK and a.long_lead_time
    assert not classify_availability("in stock", 1, 2).long_lead_time


def test_losing_visibility_is_not_reported_as_a_stock_change():
    ch = detect_availability_change(classify_availability("in stock"), classify_availability(None))
    assert [c.kind for c in ch] == [ChangeKind.OBSERVABILITY_CHANGE]
    ch = detect_availability_change(classify_availability("in stock", 2, 2), classify_availability("backorder", 20, 20))
    assert {c.kind for c in ch} == {ChangeKind.STOCK_STATE_CHANGE, ChangeKind.DELIVERY_PROMISE_CHANGE}


def sample(i, hours, status="in stock", days=60, failed=False):
    return AvailabilitySample(observation_id=f"o{i}", observed_at=T0 + timedelta(hours=hours),
                              availability=classify_availability(status, days, days), check_failed=failed)


def test_single_scrape_never_yields_a_phantom_hypothesis():
    assert phantom_inventory_hypothesis([sample(1, 0)]) is None


def test_phantom_hypothesis_needs_repeated_contradiction_over_time():
    assert phantom_inventory_hypothesis([sample(1, 0), sample(2, 0.1)]) is None      # too close together
    h = phantom_inventory_hypothesis([sample(1, 0), sample(2, 24, failed=True)])
    assert h and h.status == "HYPOTHESIS" and h.label == "POSSIBLE_PHANTOM_INVENTORY"
    assert h.confidence <= 0.7 and len(h.alternatives) >= 3 and h.supporting_observation_ids == ["o1", "o2"]
    assert "inventory" in h.caveat and "intent" in h.caveat


def test_consistent_in_stock_with_normal_delivery_is_not_flagged():
    assert phantom_inventory_hypothesis([sample(1, 0, days=2), sample(2, 24, days=2)]) is None
