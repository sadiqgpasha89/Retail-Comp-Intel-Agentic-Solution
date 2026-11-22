"""Competitor/source registry, compliance gate, rate limiting, retry and the CSV/JSON import adapter (plan section 2.1).

The gate encodes the compliance boundary: sources without an explicit, unrevoked permission are blocked, and some actions
(bypassing access controls, placing orders) are never permitted regardless of policy.
"""

from __future__ import annotations

import csv
import io
import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, Field

from retail_intel.domain.availability import classify_availability
from retail_intel.domain.observations import (CollectionMethod, Observation, Provenance, QualityFlag, new_observation, price_values, sha256_hex)
from retail_intel.domain.safety import should_quarantine


class SourceType(str, Enum):
    OFFICIAL_API = "OFFICIAL_API"
    PARTNER_FEED = "PARTNER_FEED"
    LICENSED_PROVIDER = "LICENSED_PROVIDER"
    PUBLIC_WEB = "PUBLIC_WEB"
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    DEMO = "DEMO"


# Order of preference when several sources can supply the same data (plan: APIs, feeds, licensed, public pages).
SOURCE_PREFERENCE = [SourceType.OFFICIAL_API, SourceType.PARTNER_FEED, SourceType.LICENSED_PROVIDER,
                     SourceType.PUBLIC_WEB, SourceType.MANUAL_UPLOAD, SourceType.DEMO]

NEVER_PERMITTED_ACTIONS = {"bypass_authentication", "bypass_paywall", "solve_captcha", "evade_rate_limit",
                           "place_order", "complete_checkout", "create_account", "make_payment"}


class SourcePolicy(BaseModel):
    permitted: bool = False                 # must be set explicitly; default is "not permitted"
    basis: str = ""                         # e.g. "API contract 2026-03", "ToS + robots reviewed by <name> on <date>"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    rate_limit_per_minute: int = Field(default=30, ge=1)
    allowed_actions: List[str] = Field(default_factory=lambda: ["read_listing"])


class CompetitorSource(BaseModel):
    source_id: str
    competitor_id: str
    merchant: str
    domain: Optional[str] = None
    marketplace_seller: Optional[str] = None
    country: str
    region: str = "GLOBAL"
    currency: str
    channel: str = "online"
    categories: List[str] = Field(default_factory=list)
    source_type: SourceType
    priority: int = Field(default=3, ge=1, le=5)          # 1 = highest
    schedule_cron: Optional[str] = None
    freshness_sla_hours: int = 24
    policy: SourcePolicy = Field(default_factory=SourcePolicy)


class ComplianceError(Exception):
    pass


class ComplianceGate:
    def assert_allowed(self, source: CompetitorSource, action: str = "read_listing") -> None:
        if action in NEVER_PERMITTED_ACTIONS:
            raise ComplianceError(f"Action '{action}' is never permitted")
        p = source.policy
        if source.source_type == SourceType.DEMO:
            return
        if not p.permitted or not p.basis:
            raise ComplianceError(f"Source {source.source_id}: permission not established (policy unclear)")
        if p.revoked_at is not None:
            raise ComplianceError(f"Source {source.source_id}: permission revoked {p.revoked_at.isoformat()}")
        if action not in p.allowed_actions:
            raise ComplianceError(f"Source {source.source_id}: action '{action}' not in allowed actions")


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: Dict[str, CompetitorSource] = {}

    def upsert(self, s: CompetitorSource) -> CompetitorSource:
        self._sources[s.source_id] = s
        return s

    def get(self, source_id: str) -> Optional[CompetitorSource]:
        return self._sources.get(source_id)

    def delete(self, source_id: str) -> bool:
        return self._sources.pop(source_id, None) is not None

    def list_all(self) -> List[CompetitorSource]:
        return sorted(self._sources.values(), key=lambda x: (x.priority, x.source_id))

    def list_active(self, gate: Optional[ComplianceGate] = None) -> List[CompetitorSource]:
        gate = gate or ComplianceGate()
        out = []
        for s in sorted(self._sources.values(), key=lambda x: (x.priority, x.source_id)):
            try:
                gate.assert_allowed(s)
                out.append(s)
            except ComplianceError:
                continue
        return out

    def revoke(self, source_id: str, at: Optional[datetime] = None) -> None:
        s = self._sources[source_id]
        s.policy.revoked_at = at or datetime.now(timezone.utc)


class TokenBucket:
    """Per-source rate limiter. Clock is injectable so tests are deterministic."""
    def __init__(self, per_minute: int, burst: Optional[int] = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.rate = per_minute / 60.0
        self.capacity = float(burst or per_minute)
        self.tokens = self.capacity
        self._clock, self._last = clock, clock()
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        with self._lock:
            now = self._clock()
            self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.rate)
            self._last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


def retry_with_backoff(fn: Callable[[], Any], *, attempts: int = 4, base_delay: float = 0.5, max_delay: float = 8.0,
                       retry_on: Tuple[Type[BaseException], ...] = (Exception,),
                       sleep: Callable[[float], None] = time.sleep) -> Any:
    """Bounded exponential backoff. Raises the last error after `attempts` tries; never loops forever."""
    last: Optional[BaseException] = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:  # noqa: PERF203
            last = e
            if i < attempts - 1:
                sleep(min(max_delay, base_delay * (2 ** i)))
    assert last is not None
    raise last


class SourceHealth(BaseModel):
    source_id: str
    runs: int = 0
    failures: int = 0
    parse_errors: int = 0
    quarantined: int = 0
    last_success_at: Optional[datetime] = None

    def record_run(self, ok: bool, *, parse_errors: int = 0, quarantined: int = 0, at: Optional[datetime] = None) -> None:
        self.runs += 1
        self.failures += 0 if ok else 1
        self.parse_errors += parse_errors
        self.quarantined += quarantined
        if ok:
            self.last_success_at = at or datetime.now(timezone.utc)

    def is_stale(self, sla_hours: int, now: Optional[datetime] = None) -> bool:
        """Never succeeded counts as stale: absence of data is visible, not silently substituted."""
        if self.last_success_at is None:
            return True
        return (now or datetime.now(timezone.utc)) - self.last_success_at > timedelta(hours=sla_hours)


# ---- CSV / JSON import ----------------------------------------------------------------------------------------------

REQUIRED = ("competitor_sku", "title", "price", "currency")


class RejectedRow(BaseModel):
    row: int
    reason: str


class ImportResult(BaseModel):
    payload_hash: str
    rows_total: int
    observations: List[Observation] = Field(default_factory=list)
    rejected: List[RejectedRow] = Field(default_factory=list)
    quarantined_rows: List[int] = Field(default_factory=list)


def _dec(v: Any) -> Optional[Decimal]:
    if v is None or str(v).strip() == "":
        return None
    try:
        d = Decimal(re.sub(r"[,$€£\s]", "", str(v)))
    except InvalidOperation:
        raise ValueError(f"not a number: {v!r}")
    if d < 0:
        raise ValueError(f"negative value: {v!r}")
    return d


def validate_gtin_checksum(gtin: Optional[str]) -> bool:
    d = re.sub(r"\D", "", gtin or "")
    if len(d) not in (8, 12, 13, 14):
        return False
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(d[:-1])))
    return (10 - total % 10) % 10 == int(d[-1])


def import_listings(content: bytes, fmt: str, source: CompetitorSource, *, tenant_id: str, run_id: str,
                    retrieved_at: Optional[datetime] = None, parser_version: str = "import-1.0",
                    evidence_uri: Optional[str] = None, gate: Optional[ComplianceGate] = None) -> ImportResult:
    """Parse an uploaded CSV/JSON listing file into observations. Malformed rows are rejected with a reason, never
    silently repaired; rows with injection-like text are stored but quarantined; a rejected row never becomes data."""
    (gate or ComplianceGate()).assert_allowed(source, "read_listing")
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    payload_hash = sha256_hex(content)
    if fmt.lower() == "csv":
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    elif fmt.lower() == "json":
        data = json.loads(content.decode("utf-8"))
        rows = data if isinstance(data, list) else data.get("listings", [])
    else:
        raise ValueError("fmt must be 'csv' or 'json'")

    method = CollectionMethod.DEMO_DATA if source.source_type == SourceType.DEMO else CollectionMethod.MANUAL_UPLOAD
    prov = Provenance(tenant_id=tenant_id, source_id=source.source_id, competitor_id=source.competitor_id,
                      collection_method=method, source_url=None, retrieved_at=retrieved_at, parser_version=parser_version,
                      payload_hash=payload_hash, evidence_uri=evidence_uri, run_id=run_id)
    res = ImportResult(payload_hash=payload_hash, rows_total=len(rows))
    for i, row in enumerate(rows, start=1):
        missing = [c for c in REQUIRED if str(row.get(c, "")).strip() == ""]
        if missing:
            res.rejected.append(RejectedRow(row=i, reason=f"missing required: {', '.join(missing)}"))
            continue
        try:
            price = _dec(row["price"])
            list_price = _dec(row.get("list_price")) or price
            ship = _dec(row.get("shipping_fee"))
            observed = datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00")) if row.get("observed_at") else retrieved_at
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            pack = int(row["pack_size"]) if str(row.get("pack_size", "")).strip() else None
            dmin = int(row["delivery_days"]) if str(row.get("delivery_days", "")).strip() else None
        except (ValueError, TypeError) as e:
            res.rejected.append(RejectedRow(row=i, reason=str(e)))
            continue
        if not price or price <= 0:
            res.rejected.append(RejectedRow(row=i, reason="price must be positive"))
            continue
        flags: List[QualityFlag] = []
        scan = should_quarantine(str(row.get("title", "")), str(row.get("description", "")), str(row.get("category", "")))
        if scan.suspicious:
            flags += [QualityFlag.SUSPICIOUS_CONTENT, QualityFlag.QUARANTINED]
            res.quarantined_rows.append(i)
        gtin = str(row.get("gtin", "")).strip()
        if gtin and not validate_gtin_checksum(gtin):
            flags.append(QualityFlag.UNVERIFIED_GTIN)
        listing_id = str(row["competitor_sku"]).strip()
        region = str(row.get("region") or source.region)
        pv = price_values(list_price=list_price, sale_price=price if price < list_price else None, shipping_fee=ship, pack_size=pack)
        pv.update({"title": str(row["title"])[:500], "brand": row.get("brand"), "category": row.get("category"),
                   "gtin": gtin or None, "url": row.get("url")})
        res.observations.append(new_observation("price", prov, listing_id, observed, pv, region, str(row["currency"]), flags))
        if str(row.get("availability", "")).strip() or dmin is not None:
            av = classify_availability(row.get("availability"), dmin, dmin)
            res.observations.append(new_observation("availability", prov, listing_id, observed,
                                                    json.loads(av.model_dump_json()), region, None, flags))
        if row.get("offers"):
            offers = row["offers"]
            try:
                offers = json.loads(offers) if isinstance(offers, str) else offers
            except json.JSONDecodeError:
                res.rejected.append(RejectedRow(row=i, reason="offers column is not valid JSON (price row kept)"))
                continue
            res.observations.append(new_observation("promotion", prov, listing_id, observed, {"offers": offers}, region,
                                                    str(row["currency"]), flags))
    return res
