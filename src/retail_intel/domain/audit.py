"""Append-only, hash-chained audit log (plan sections 3 and 8: immutable audit events)."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
import uuid

from pydantic import BaseModel, Field

from retail_intel.domain.observations import canonical_json, sha256_hex

GENESIS_HASH = "0" * 64


class AuditEvent(BaseModel):
    event_id: str
    ts: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    hash: str


def _payload(e: AuditEvent | Dict[str, Any]) -> Dict[str, Any]:
    d = e.model_dump(mode="json") if isinstance(e, AuditEvent) else dict(e)
    return {k: d[k] for k in ("event_id", "ts", "actor", "action", "entity_type", "entity_id", "details", "prev_hash")}


def compute_hash(e: AuditEvent | Dict[str, Any]) -> str:
    return sha256_hex(canonical_json(_payload(e)))


class AuditSink(Protocol):
    def append(self, event: AuditEvent) -> None: ...
    def all(self, entity_id: Optional[str] = None) -> List[AuditEvent]: ...
    def last_hash(self) -> str: ...


class InMemoryAuditSink:
    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def all(self, entity_id: Optional[str] = None) -> List[AuditEvent]:
        return [e for e in self._events if entity_id is None or e.entity_id == entity_id]

    def last_hash(self) -> str:
        return self._events[-1].hash if self._events else GENESIS_HASH


class AuditLog:
    def __init__(self, sink: Optional[AuditSink] = None) -> None:
        self.sink: AuditSink = sink or InMemoryAuditSink()
        self._lock = threading.Lock()

    def record(self, actor: str, action: str, entity_type: str, entity_id: str,
               details: Optional[Dict[str, Any]] = None, ts: Optional[datetime] = None) -> AuditEvent:
        with self._lock:
            prev = self.sink.last_hash()
            ev = AuditEvent(event_id=f"aud_{uuid.uuid4().hex}", ts=ts or datetime.now(timezone.utc), actor=actor,
                            action=action, entity_type=entity_type, entity_id=entity_id,
                            details=details or {}, prev_hash=prev, hash="")
            ev.hash = compute_hash(ev)
            self.sink.append(ev)
            return ev

    def events(self, entity_id: Optional[str] = None) -> List[AuditEvent]:
        return self.sink.all(entity_id)

    def verify(self) -> bool:
        """True when every event hashes correctly and links to its predecessor."""
        prev = GENESIS_HASH
        for e in self.sink.all():
            if e.prev_hash != prev or compute_hash(e) != e.hash:
                return False
            prev = e.hash
        return True
