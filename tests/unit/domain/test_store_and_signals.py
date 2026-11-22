"""Acceptance scenarios 1, 2 and 7: persisted evidence-backed observations, price change detection, multi-source insight."""
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from retail_intel.domain.audit import AuditLog
from retail_intel.domain.observations import (CollectionMethod, Provenance, QualityFlag, new_observation, price_values)
from retail_intel.domain.signals import (CatalogListing, assortment_gaps, category_coverage, detect_price_changes,
                                         discount_depth_pct, hypothesize_price_move, new_and_delisted,
                                         observed_share_of_assortment, price_gap_pct, price_index, promotion_frequency,
                                         robust_price_anomaly, volatility, weighted_price_index)
from retail_intel.domain.store import ObservationStore

pytestmark = pytest.mark.unit
T0 = datetime(2026, 3, 1, 9, tzinfo=timezone.utc)


def prov(store, hours=0, source="s1", comp="c1", method=CollectionMethod.PARTNER_FEED, payload="p"):
    uri, h = store.put_evidence({"payload": payload, "h": hours})
    return Provenance(tenant_id="t1", source_id=source, competitor_id=comp, collection_method=method,
                      source_url="https://feed.example/x", retrieved_at=T0 + timedelta(hours=hours, minutes=5),
                      parser_version="p-1", payload_hash=h, evidence_uri=uri)


def price_obs(store, hours, price, sale=None, observed=None, **kw):
    """`hours` = when we retrieved it; `observed` = when the source showed it (defaults to the same hour)."""
    obs_h = hours if observed is None else observed
    return new_observation("price", prov(store, hours, payload=f"{hours}-{price}", **kw), "SKU-A", T0 + timedelta(hours=obs_h),
                           price_values(list_price=price, sale_price=sale), currency="USD")


def test_observation_round_trip_keeps_full_provenance_and_is_idempotent():
    s = ObservationStore()
    o = price_obs(s, 0, "100.00")
    assert s.append_observation(o) is True and s.append_observation(o) is False
    got = s.history(tenant_id="t1", kind="price", listing_id="SKU-A")
    assert len(got) == 1
    p = got[0].provenance
    assert p.parser_version == "p-1" and p.evidence_uri.startswith("evidence://sha256/") and p.retrieved_at > got[0].observed_at
    assert s.get_evidence(p.payload_hash) is not None


def test_as_of_queries_are_reproducible_and_ignore_late_arriving_data():
    s = ObservationStore()
    for h, p in [(0, "100"), (24, "95"), (48, "90")]:
        s.append_observation(price_obs(s, h, p))
    as_of = T0 + timedelta(hours=30)
    first = [o.observation_id for o in s.history(tenant_id="t1", kind="price", listing_id="SKU-A", as_of=as_of)]
    s.append_observation(price_obs(s, 40, "50", observed=20))  # observed earlier but retrieved after as_of
    again = [o.observation_id for o in s.history(tenant_id="t1", kind="price", listing_id="SKU-A", as_of=as_of)]
    assert first == again and len(first) == 2


def test_observations_and_audit_are_immutable_in_the_database():
    s = ObservationStore()
    s.append_observation(price_obs(s, 0, "100"))
    with pytest.raises(sqlite3.DatabaseError):
        s._conn.execute("UPDATE observation SET listing_id='X'")
    with pytest.raises(sqlite3.DatabaseError):
        s._conn.execute("DELETE FROM evidence")
    AuditLog(s).record("a", "x", "e", "1")
    with pytest.raises(sqlite3.DatabaseError):
        s._conn.execute("DELETE FROM audit_event")


def test_quarantined_records_are_retained_but_excluded_by_default():
    s = ObservationStore()
    q = new_observation("price", prov(s, 0), "SKU-A", T0, price_values(list_price="1.00"), currency="USD",
                        quality_flags=[QualityFlag.QUARANTINED, QualityFlag.SUSPICIOUS_CONTENT])
    s.append_observation(q)
    assert s.history(tenant_id="t1", kind="price", listing_id="SKU-A") == []
    assert len(s.history(tenant_id="t1", kind="price", listing_id="SKU-A", include_quarantined=True)) == 1


def test_naive_timestamps_rejected_and_demo_data_is_labelled():
    s = ObservationStore()
    with pytest.raises(ValueError):
        s.history(tenant_id="t1", kind="price", listing_id="x", as_of=datetime(2026, 1, 1))
    d = price_obs(s, 0, "10", method=CollectionMethod.DEMO_DATA)
    assert QualityFlag.DEMO_DATA in d.quality_flags
    s.append_observation(d)
    assert s.count_observations(demo_only=True) == 1


def test_price_change_shows_before_after_source_time_and_unit_price():
    s = ObservationStore()
    for h, p, sale in [(0, "100.00", None), (24, "100.00", "88.00"), (48, "100.00", "88.00")]:
        s.append_observation(price_obs(s, h, p, sale))
    ch = detect_price_changes(s.history(tenant_id="t1", kind="price", listing_id="SKU-A"))
    assert len(ch) == 1
    c = ch[0]
    assert (c.before_price, c.after_price, c.pct_change, c.direction) == (D("100.00"), D("88.00"), D("-12.00"), "DROP")
    assert c.source_id == "s1" and c.after_observed_at == T0 + timedelta(hours=24) and len(c.evidence_ids) == 2


def test_price_changes_skip_cross_source_and_cross_currency_pairs():
    s = ObservationStore()
    s.append_observation(price_obs(s, 0, "100", source="a"))
    s.append_observation(price_obs(s, 1, "50", source="b"))
    assert detect_price_changes(s.history(tenant_id="t1", kind="price", listing_id="SKU-A")) == []


def test_gap_index_depth_frequency_volatility():
    assert price_gap_pct("100", "95") == D("-5.00") and price_index("100", "95") == D("95.00")
    assert discount_depth_pct("100", "80") == D("20.00") and discount_depth_pct("100", "120") == D("0.00")
    assert weighted_price_index([(D(100), D(90), D(3)), (D(100), D(110), D(1))]) == D("95.00") and weighted_price_index([]) is None
    s = ObservationStore()
    for h, p, sale in [(0, "100", None), (1, "100", "90"), (2, "100", None), (3, "100", "90")]:
        s.append_observation(price_obs(s, h, p, sale))
    assert promotion_frequency(s.history(tenant_id="t1", kind="price", listing_id="SKU-A")) == 0.5
    assert volatility([D(100), D(90), D(100), D(90), D(100)])["reversals"] == 3


def test_robust_anomaly_needs_history_and_explains_itself():
    assert robust_price_anomaly([D(10)] * 3, D(1)) is None
    hist = [D(v) for v in (100, 101, 99, 100, 102, 98, 100)]
    ok = robust_price_anomaly(hist, D(101))
    bad = robust_price_anomaly(hist, D(40))
    assert ok and not ok.is_anomaly and bad and bad.is_anomaly and bad.pct_vs_median < 0
    assert {"robust_z", "pct_vs_median", "history_points"} <= set(bad.contributing_features)


def test_assortment_gaps_coverage_and_defensible_share():
    ls = [CatalogListing(listing_id=f"L{i}", competitor_id="c1", category="Audio", brand="Zed") for i in range(3)] + \
         [CatalogListing(listing_id="L9", competitor_id="c1", category="TV", brand="Q")]
    gaps = assortment_gaps(ls, {"L0"})
    assert (gaps[0].category, gaps[0].unmatched_listing_count) == ("Audio", 2)
    assert category_coverage({"Audio": {"a", "b"}, "TV": {"c"}}, {"a"}) == {"Audio": 0.5, "TV": 0.0}
    assert observed_share_of_assortment(50, 200, 0.9) == 0.25
    assert observed_share_of_assortment(50, None, 0.9) is None and observed_share_of_assortment(50, 200, 0.4) is None
    assert new_and_delisted({"a", "b"}, {"b", "c"}) == {"new": ["c"], "delisted_or_unobserved": ["a"]}


def test_hypotheses_are_labelled_capped_and_carry_alternatives():
    s = ObservationStore()
    s.append_observation(price_obs(s, 0, "100"))
    s.append_observation(price_obs(s, 24, "50"))
    c = detect_price_changes(s.history(tenant_id="t1", kind="price", listing_id="SKU-A"))[0]
    hyps = hypothesize_price_move(c, corroborating_sources=0)
    assert hyps and hyps[0].label == "POSSIBLE_DATA_ARTEFACT"
    for h in hypotheses_for(c):
        assert h.status == "HYPOTHESIS" and h.confidence <= 0.6 and h.alternatives and h.caveat


def hypotheses_for(c):
    return hypothesize_price_move(c, corroborating_sources=2) + hypothesize_price_move(c, concurrent_promotion=True, corroborating_sources=3)
