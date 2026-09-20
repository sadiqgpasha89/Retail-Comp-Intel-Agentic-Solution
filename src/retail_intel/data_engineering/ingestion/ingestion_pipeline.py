"""Headless Ingestion Pipeline: harvests unstructured PDPs, detects honeypots, and validates payload integrity."""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.core.providers import BaseStorageProvider, get_storage_provider

logger = get_logger("data_engineering.ingestion")

# Limit concurrent ingest coroutines to avoid overwhelming downstream systems
_INGEST_SEMAPHORE_SIZE = 32


class IngestionPayload(BaseModel):
    """Raw competitor crawled item payload."""
    competitor_id: str
    competitor_name: str
    competitor_sku: str
    gtin: Optional[str] = None
    title: str
    brand: str
    raw_category: str
    scraped_base_price: float
    on_page_coupon: float = 0.0
    cart_discount: float = 0.0
    final_effective_price: float
    unit_measure: str = "count"
    pack_size: int = 1
    stock_status: str = "IN_STOCK"
    fulfillment_latency_days: int = 2
    pdp_url: str
    image_url: str = ""
    specifications: Dict[str, Any] = Field(default_factory=dict)
    customer_reviews_summary: str = ""
    is_honeypot: bool = False
    is_phantom_stock: bool = False


class RawCrawlEvent(BaseModel):
    """Event envelope emitted downstream into stream broker and storage."""
    event_id: str
    timestamp: float
    payload: IngestionPayload
    storage_uri: str
    payload_hash: str
    honeypot_flag: bool
    phantom_flag: bool


class IngestionPipeline:
    """Enterprise Ingestion Engine with honeypot defense and phantom inventory verification."""

    def __init__(self, storage: Optional[BaseStorageProvider] = None):
        self.storage = storage or get_storage_provider()
        self.ingested_count: int = 0
        self.honeypots_intercepted: int = 0
        self.phantoms_intercepted: int = 0
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Lazily initialise semaphore inside the running event loop."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(_INGEST_SEMAPHORE_SIZE)
        return self._semaphore

    def detect_honeypot(self, payload: IngestionPayload) -> bool:
        """Flags honeypot defense mechanisms (synthetic crawler bait)."""
        if payload.is_honeypot:
            return True
        specs = payload.specifications or {}
        if specs.get("bot_trap") == "true" or specs.get("dom_fingerprint_scrambled") == "true":
            return True
        if "trap" in payload.pdp_url.lower() or "honeypot" in payload.title.lower():
            return True
        return False

    def detect_phantom_stock(self, payload: IngestionPayload) -> bool:
        """Flags unfulfilled phantom stock listings (predatory algorithmic bot lures)."""
        if payload.is_phantom_stock:
            return True
        if payload.stock_status in ["BACKORDER", "OUT_OF_STOCK"] and payload.fulfillment_latency_days >= 30:
            return True
        specs = payload.specifications or {}
        if "sold out" in str(specs.get("stock_flag", "")).lower():
            return True
        return False

    async def ingest_record(self, raw_data: Dict[str, Any]) -> RawCrawlEvent:
        """Processes a single raw crawl document, persists to data lake, and returns structured event."""
        payload = IngestionPayload(**raw_data)
        self.ingested_count += 1

        is_honeypot = self.detect_honeypot(payload)
        is_phantom = self.detect_phantom_stock(payload)

        if is_honeypot:
            self.honeypots_intercepted += 1
            logger.warning(
                "Adversarial honeypot trap intercepted",
                sku=payload.competitor_sku,
                comp=payload.competitor_name,
            )

        if is_phantom:
            self.phantoms_intercepted += 1
            logger.warning(
                "Phantom stock listing flagged",
                sku=payload.competitor_sku,
                latency_days=payload.fulfillment_latency_days,
            )

        payload_bytes = json.dumps(payload.model_dump(), sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        event_id = f"evt_{payload.competitor_sku}_{int(time.time() * 1000)}"

        storage_key = f"raw_ingest/{payload.competitor_id}/{event_id}.json"
        storage_uri = await self.storage.put_payload(storage_key, payload.model_dump())

        return RawCrawlEvent(
            event_id=event_id,
            timestamp=time.time(),
            payload=payload,
            storage_uri=storage_uri,
            payload_hash=payload_hash,
            honeypot_flag=is_honeypot,
            phantom_flag=is_phantom,
        )

    async def run_batch(self, records: List[Dict[str, Any]]) -> List[RawCrawlEvent]:
        """
        Ingests a batch of records with bounded concurrency via asyncio.gather + semaphore.
        Replaces the previous sequential for-loop that was a hard throughput bottleneck.
        """
        sem = self._get_semaphore()

        async def _bounded_ingest(raw: Dict[str, Any]) -> RawCrawlEvent:
            async with sem:
                return await self.ingest_record(raw)

        events: List[RawCrawlEvent] = await asyncio.gather(
            *[_bounded_ingest(r) for r in records],
            return_exceptions=False,
        )

        logger.info(
            "Batch ingestion completed",
            total=len(records),
            honeypots=self.honeypots_intercepted,
            phantoms=self.phantoms_intercepted,
        )
        return list(events)
