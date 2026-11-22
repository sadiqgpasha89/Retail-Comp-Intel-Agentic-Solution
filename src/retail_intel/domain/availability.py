"""Availability and fulfilment semantics (plan section 2.5).

Principles enforced here: UNKNOWN is not OUT_OF_STOCK; a long lead time is a separate flag, not a stock state;
"phantom inventory" is a labelled hypothesis needing corroboration; actual stock quantities are never inferred.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AvailabilityState(str, Enum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PREORDER = "PREORDER"
    BACKORDER = "BACKORDER"
    UNKNOWN = "UNKNOWN"          # not observed / unparseable / check failed. Never treated as unavailable.


_STATUS_MAP = {
    "in stock": AvailabilityState.IN_STOCK, "in_stock": AvailabilityState.IN_STOCK, "instock": AvailabilityState.IN_STOCK,
    "available": AvailabilityState.IN_STOCK,
    "low stock": AvailabilityState.LOW_STOCK, "low_stock": AvailabilityState.LOW_STOCK,
    "limited stock": AvailabilityState.LOW_STOCK, "only few left": AvailabilityState.LOW_STOCK,
    "out of stock": AvailabilityState.OUT_OF_STOCK, "out_of_stock": AvailabilityState.OUT_OF_STOCK,
    "outofstock": AvailabilityState.OUT_OF_STOCK, "sold out": AvailabilityState.OUT_OF_STOCK,
    "preorder": AvailabilityState.PREORDER, "pre-order": AvailabilityState.PREORDER, "pre_order": AvailabilityState.PREORDER,
    "backorder": AvailabilityState.BACKORDER, "back-order": AvailabilityState.BACKORDER,
    "back_order": AvailabilityState.BACKORDER,
}


class Availability(BaseModel):
    state: AvailabilityState
    delivery_days_min: Optional[int] = None
    delivery_days_max: Optional[int] = None
    long_lead_time: bool = False
    raw_status: Optional[str] = None
    note: Optional[str] = None


def classify_availability(raw_status: Optional[str], delivery_days_min: Optional[int] = None,
                          delivery_days_max: Optional[int] = None, long_lead_days: int = 21) -> Availability:
    """Map a source status string to a state. Unrecognised or missing statuses become UNKNOWN."""
    key = (raw_status or "").strip().lower()
    state = _STATUS_MAP.get(key, AvailabilityState.UNKNOWN)
    note = None if state != AvailabilityState.UNKNOWN else (
        "status not observed" if not key else f"unrecognised status '{raw_status}'")
    worst = delivery_days_max if delivery_days_max is not None else delivery_days_min
    return Availability(state=state, delivery_days_min=delivery_days_min, delivery_days_max=delivery_days_max,
                        long_lead_time=worst is not None and worst >= long_lead_days, raw_status=raw_status, note=note)


class ChangeKind(str, Enum):
    STOCK_STATE_CHANGE = "STOCK_STATE_CHANGE"
    DELIVERY_PROMISE_CHANGE = "DELIVERY_PROMISE_CHANGE"
    OBSERVABILITY_CHANGE = "OBSERVABILITY_CHANGE"   # to/from UNKNOWN: we lost or regained visibility, stock did not necessarily change


class AvailabilityChange(BaseModel):
    kind: ChangeKind
    before: Availability
    after: Availability
    detail: str


def detect_availability_change(before: Availability, after: Availability,
                               delivery_delta_days: int = 3) -> List[AvailabilityChange]:
    out: List[AvailabilityChange] = []
    if before.state != after.state:
        if AvailabilityState.UNKNOWN in (before.state, after.state):
            out.append(AvailabilityChange(kind=ChangeKind.OBSERVABILITY_CHANGE, before=before, after=after,
                                          detail=f"{before.state.value} -> {after.state.value} (visibility change, not a stock claim)"))
        else:
            out.append(AvailabilityChange(kind=ChangeKind.STOCK_STATE_CHANGE, before=before, after=after,
                                          detail=f"{before.state.value} -> {after.state.value}"))
    b, a = before.delivery_days_max, after.delivery_days_max
    if b is not None and a is not None and abs(a - b) >= delivery_delta_days:
        out.append(AvailabilityChange(kind=ChangeKind.DELIVERY_PROMISE_CHANGE, before=before, after=after,
                                      detail=f"delivery promise {b}d -> {a}d"))
    return out


class AvailabilitySample(BaseModel):
    observation_id: str
    observed_at: datetime
    availability: Availability
    check_failed: bool = False       # a permitted availability recheck failed (e.g. cart check refused the item)


class Hypothesis(BaseModel):
    label: str
    status: str = "HYPOTHESIS"        # never "FACT"
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_observation_ids: List[str]
    alternatives: List[str]
    caveat: str


def phantom_inventory_hypothesis(samples: List[AvailabilitySample], min_samples: int = 2,
                                 min_span_hours: float = 1.0) -> Optional[Hypothesis]:
    """A listing that *displays* stock while delivery is very long or rechecks fail, repeatedly over time.

    Returns None when evidence is insufficient (a single scrape is never enough). Output is always a hypothesis
    with alternatives, and never an inventory quantity.
    """
    contradictory = [s for s in samples if (
        s.availability.state in (AvailabilityState.IN_STOCK, AvailabilityState.LOW_STOCK)
        and (s.availability.long_lead_time or s.check_failed))]
    if len(contradictory) < min_samples:
        return None
    span = (max(s.observed_at for s in contradictory) - min(s.observed_at for s in contradictory)).total_seconds() / 3600
    if span < min_span_hours:
        return None
    confidence = min(0.7, 0.35 + 0.1 * (len(contradictory) - min_samples) + (0.1 if any(s.check_failed for s in contradictory) else 0))
    return Hypothesis(
        label="POSSIBLE_PHANTOM_INVENTORY", confidence=round(confidence, 2),
        supporting_observation_ids=[s.observation_id for s in contradictory],
        alternatives=["Genuine long supplier lead time", "Regional or store-level stock variation",
                      "Stale or cached page state", "Parser / data artefact"],
        caveat="Displayed availability conflicts with delivery promise or recheck results across multiple observations. "
               "This does not establish actual competitor inventory or intent.")
