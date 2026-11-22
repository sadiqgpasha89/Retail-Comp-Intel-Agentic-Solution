"""Competitive signals: price moves, gaps, indices, assortment and labelled hypotheses (plan section 2.6).

Facts (a price changed from A to B) are separated from hypotheses (why). Hypotheses always carry alternatives,
a capped confidence and a caveat; none of them claims competitor intent.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from retail_intel.domain.availability import AvailabilityState, Hypothesis
from retail_intel.domain.observations import Observation, QualityFlag


def effective_listing_price(obs: Observation) -> Decimal:
    """Price a shopper would see for this observation: sale price if present, else list price."""
    v = obs.values
    return Decimal(str(v["sale_price"] if v.get("sale_price") is not None else v["list_price"]))


class PriceChange(BaseModel):
    listing_id: str
    currency: Optional[str]
    before_price: Decimal
    after_price: Decimal
    abs_change: Decimal
    pct_change: Decimal
    direction: str
    before_observation_id: str
    after_observation_id: str
    before_observed_at: datetime
    after_observed_at: datetime
    source_id: str
    evidence_ids: List[str] = Field(default_factory=list)


def detect_price_changes(history: List[Observation], min_pct: Decimal = Decimal("1")) -> List[PriceChange]:
    """Compare consecutive usable price observations from the same source. Currency changes are not compared."""
    usable = [o for o in history if o.kind == "price" and o.is_usable]
    out: List[PriceChange] = []
    for a, b in zip(usable, usable[1:]):
        if a.currency != b.currency or a.provenance.source_id != b.provenance.source_id:
            continue
        pa, pb = effective_listing_price(a), effective_listing_price(b)
        if pa == 0:
            continue
        pct = (pb - pa) / pa * 100
        if abs(pct) >= min_pct:
            out.append(PriceChange(
                listing_id=b.listing_id, currency=b.currency, before_price=pa, after_price=pb, abs_change=pb - pa,
                pct_change=pct.quantize(Decimal("0.01")), direction="DROP" if pb < pa else "RISE",
                before_observation_id=a.observation_id, after_observation_id=b.observation_id,
                before_observed_at=a.observed_at, after_observed_at=b.observed_at, source_id=b.provenance.source_id,
                evidence_ids=[e for e in (a.provenance.evidence_uri, b.provenance.evidence_uri) if e]))
    return out


def price_gap_pct(our_price: Decimal | str, competitor_price: Decimal | str) -> Decimal:
    """Positive = competitor is more expensive than us; negative = competitor undercuts us."""
    o = Decimal(str(our_price))
    return ((Decimal(str(competitor_price)) - o) / o * 100).quantize(Decimal("0.01"))


def price_index(our_price: Decimal | str, competitor_price: Decimal | str) -> Decimal:
    """Competitor price as % of ours (100 = parity, <100 = competitor cheaper)."""
    return (Decimal(str(competitor_price)) / Decimal(str(our_price)) * 100).quantize(Decimal("0.01"))


def weighted_price_index(pairs: List[tuple[Decimal, Decimal, Decimal]]) -> Optional[Decimal]:
    """pairs = (our_price, competitor_price, weight). Weight is e.g. our unit sales; returns None without pairs."""
    tot = sum((w for _, _, w in pairs), Decimal(0))
    if not pairs or tot == 0:
        return None
    return (sum((price_index(o, c) * w for o, c, w in pairs), Decimal(0)) / tot).quantize(Decimal("0.01"))


def discount_depth_pct(list_price: Decimal | str, sale_price: Decimal | str) -> Decimal:
    lp = Decimal(str(list_price))
    return max(Decimal(0), (lp - Decimal(str(sale_price))) / lp * 100).quantize(Decimal("0.01"))


def promotion_frequency(history: List[Observation]) -> Optional[float]:
    prices = [o for o in history if o.kind == "price" and o.is_usable]
    if not prices:
        return None
    on_promo = sum(1 for o in prices if o.values.get("sale_price") is not None
                   and Decimal(str(o.values["sale_price"])) < Decimal(str(o.values["list_price"])))
    return on_promo / len(prices)


def volatility(prices: List[Decimal]) -> Dict[str, float]:
    """Coefficient of variation and direction reversals (a crude oscillation indicator)."""
    if len(prices) < 3:
        return {"cv": 0.0, "reversals": 0}
    f = [float(p) for p in prices]
    mean = statistics.fmean(f)
    cv = statistics.pstdev(f) / mean if mean else 0.0
    diffs = [b - a for a, b in zip(f, f[1:]) if b != a]
    reversals = sum(1 for x, y in zip(diffs, diffs[1:]) if (x > 0) != (y > 0))
    return {"cv": round(cv, 4), "reversals": reversals}


class AnomalyResult(BaseModel):
    is_anomaly: bool
    robust_z: float
    median: Decimal
    mad: Decimal
    pct_vs_median: Decimal
    contributing_features: Dict[str, float]


def robust_price_anomaly(history_prices: List[Decimal], new_price: Decimal, z_threshold: float = 3.5,
                         min_history: int = 5) -> Optional[AnomalyResult]:
    """Median/MAD z-score. Returns None with too little history (no verdict is better than a weak one)."""
    if len(history_prices) < min_history:
        return None
    f = [float(p) for p in history_prices]
    med = statistics.median(f)
    mad = statistics.median([abs(x - med) for x in f])
    scale = 1.4826 * mad if mad > 0 else max(abs(med) * 0.01, 1e-9)   # floor so flat history is not infinitely sensitive
    z = (float(new_price) - med) / scale
    pct = Decimal(str(round((float(new_price) - med) / med * 100, 2))) if med else Decimal(0)
    return AnomalyResult(is_anomaly=abs(z) >= z_threshold, robust_z=round(z, 2), median=Decimal(str(round(med, 4))),
                         mad=Decimal(str(round(mad, 4))), pct_vs_median=pct,
                         contributing_features={"robust_z": round(z, 2), "pct_vs_median": float(pct), "history_points": float(len(f))})


class CatalogListing(BaseModel):
    listing_id: str
    competitor_id: str
    category: str
    brand: Optional[str] = None


class AssortmentGap(BaseModel):
    category: str
    brand: Optional[str]
    unmatched_listing_count: int
    example_listing_ids: List[str]


def assortment_gaps(competitor_listings: List[CatalogListing], matched_listing_ids: Set[str]) -> List[AssortmentGap]:
    """Competitor listings with no match to our catalogue, grouped by category and brand (candidate range gaps)."""
    groups: Dict[tuple, List[str]] = {}
    for l in competitor_listings:
        if l.listing_id not in matched_listing_ids:
            groups.setdefault((l.category, l.brand), []).append(l.listing_id)
    gaps = [AssortmentGap(category=c, brand=b, unmatched_listing_count=len(ids), example_listing_ids=sorted(ids)[:5])
            for (c, b), ids in groups.items()]
    return sorted(gaps, key=lambda g: (-g.unmatched_listing_count, g.category, g.brand or ""))


def category_coverage(our_skus_by_category: Dict[str, Set[str]], skus_with_competitor_match: Set[str]) -> Dict[str, float]:
    """Share of OUR SKUs per category that have at least one competitor match."""
    return {c: (len(s & skus_with_competitor_match) / len(s) if s else 0.0) for c, s in our_skus_by_category.items()}


def observed_share_of_assortment(competitor_listing_count: int, known_universe_size: Optional[int],
                                 source_coverage_ratio: Optional[float], min_coverage: float = 0.8) -> Optional[float]:
    """Only reported when the denominator is defensible: known universe size AND adequate source coverage."""
    if not known_universe_size or source_coverage_ratio is None or source_coverage_ratio < min_coverage:
        return None
    return competitor_listing_count / known_universe_size


def new_and_delisted(previous_ids: Set[str], current_ids: Set[str]) -> Dict[str, List[str]]:
    return {"new": sorted(current_ids - previous_ids), "delisted_or_unobserved": sorted(previous_ids - current_ids)}


def hypothesize_price_move(change: PriceChange, *, concurrent_promotion: bool = False,
                           availability: Optional[AvailabilityState] = None, corroborating_sources: int = 0,
                           quality_flags: Optional[List[QualityFlag]] = None) -> List[Hypothesis]:
    """Candidate explanations for a price move, each labelled HYPOTHESIS with alternatives. Intent is never asserted."""
    sup = [change.before_observation_id, change.after_observation_id]
    cap = 0.6
    out: List[Hypothesis] = []
    drop = change.direction == "DROP"
    sharp = abs(change.pct_change) >= Decimal("40")
    flagged = bool(quality_flags and (QualityFlag.SUSPICIOUS_CONTENT in quality_flags or QualityFlag.UNVERIFIED_GTIN in quality_flags))

    if sharp and (corroborating_sources == 0 or flagged):
        out.append(Hypothesis(label="POSSIBLE_DATA_ARTEFACT", confidence=0.5, supporting_observation_ids=sup,
                              alternatives=["Genuine clearance", "Aggressive price competition"],
                              caveat="Large single-source move without corroboration; verify before acting."))
    if drop and concurrent_promotion:
        out.append(Hypothesis(label="PROMOTION_LED_ACQUISITION", confidence=min(cap, 0.45 + 0.05 * corroborating_sources),
                              supporting_observation_ids=sup, alternatives=["Permanent price reduction", "Data artefact"],
                              caveat="A promotion was observed concurrently; its end date is unknown."))
    if drop and availability in (AvailabilityState.LOW_STOCK, AvailabilityState.OUT_OF_STOCK):
        out.append(Hypothesis(label="POSSIBLE_CLEARANCE_OR_LIQUIDATION", confidence=0.4, supporting_observation_ids=sup,
                              alternatives=["Supply disruption", "Aggressive price competition"],
                              caveat="Falling stock with falling price is consistent with clearance but does not prove it."))
    if drop and not out:
        out.append(Hypothesis(label="POSSIBLE_AGGRESSIVE_PRICE_COMPETITION",
                              confidence=min(cap, 0.3 + 0.1 * corroborating_sources), supporting_observation_ids=sup,
                              alternatives=["Temporary promotion", "Clearance", "Cost reduction", "Data artefact"],
                              caveat="Correlation only; competitor intent is not established."))
    return out
