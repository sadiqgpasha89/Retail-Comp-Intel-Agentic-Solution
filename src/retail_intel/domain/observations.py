"""Immutable, provenance-carrying observations (plan section 5).

Observations are append-only facts about what a source showed at a time. They are never edited; corrections are new
observations. Quarantined records stay stored (evidence is never deleted) but are flagged.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CollectionMethod(str, Enum):
    OFFICIAL_API = "OFFICIAL_API"
    PARTNER_FEED = "PARTNER_FEED"
    LICENSED_PROVIDER = "LICENSED_PROVIDER"
    PUBLIC_WEB_PAGE = "PUBLIC_WEB_PAGE"
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    DEMO_DATA = "DEMO_DATA"


class QualityFlag(str, Enum):
    QUARANTINED = "QUARANTINED"
    SUSPICIOUS_CONTENT = "SUSPICIOUS_CONTENT"
    UNVERIFIED_GTIN = "UNVERIFIED_GTIN"
    MISSING_FIELD = "MISSING_FIELD"
    DEMO_DATA = "DEMO_DATA"
    STALE = "STALE"


class Provenance(BaseModel):
    tenant_id: str
    source_id: str
    competitor_id: str
    collection_method: CollectionMethod
    source_url: Optional[str] = None
    retrieved_at: datetime
    source_timestamp: Optional[datetime] = None      # when the source says the data is from, if it says
    parser_version: str
    payload_hash: str
    evidence_uri: Optional[str] = None
    run_id: Optional[str] = None


ObsKind = Literal["price", "promotion", "availability", "fulfilment"]


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False)


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


class Observation(BaseModel):
    """One immutable observation. `values` holds the kind-specific payload (see helpers below)."""
    observation_id: str
    kind: ObsKind
    listing_id: str                      # competitor SKU / listing key within the competitor
    region: str = "GLOBAL"
    currency: Optional[str] = None
    observed_at: datetime
    values: Dict[str, Any]
    provenance: Provenance
    quality_flags: List[QualityFlag] = Field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return QualityFlag.QUARANTINED not in self.quality_flags


def make_observation_id(kind: str, provenance: Provenance, listing_id: str, region: str, values: Dict[str, Any]) -> str:
    """Deterministic ID: re-ingesting the identical payload yields the same ID (idempotent)."""
    digest = sha256_hex(canonical_json([kind, provenance.source_id, listing_id, region, provenance.payload_hash, values]))
    return f"obs_{kind[:3]}_{digest[:20]}"


def price_values(list_price: Decimal | str, sale_price: Decimal | str | None = None, reference_price: Decimal | str | None = None,
                 shipping_fee: Decimal | str | None = None, unit_price: Decimal | str | None = None,
                 unit_measure: str | None = None, pack_size: int | None = None,
                 tax_treatment: str = "UNKNOWN") -> Dict[str, Any]:
    d = {"list_price": list_price, "sale_price": sale_price, "reference_price": reference_price,
         "shipping_fee": shipping_fee, "unit_price": unit_price, "unit_measure": unit_measure,
         "pack_size": pack_size, "tax_treatment": tax_treatment}
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in d.items() if v is not None}


def new_observation(kind: ObsKind, provenance: Provenance, listing_id: str, observed_at: datetime, values: Dict[str, Any],
                    region: str = "GLOBAL", currency: str | None = None,
                    quality_flags: Optional[List[QualityFlag]] = None) -> Observation:
    flags = list(quality_flags or [])
    if provenance.collection_method == CollectionMethod.DEMO_DATA and QualityFlag.DEMO_DATA not in flags:
        flags.append(QualityFlag.DEMO_DATA)
    return Observation(observation_id=make_observation_id(kind, provenance, listing_id, region, values), kind=kind,
                       listing_id=listing_id, region=region, currency=currency, observed_at=observed_at,
                       values=values, provenance=provenance, quality_flags=flags)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
