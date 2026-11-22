"""SQLite-backed append-only store: observations, content-addressed evidence, recommendations, audit events.

SQLite is the local/dev provider. The same repository surface is what a Cloud SQL / BigQuery adapter would implement
(see docs/SADR.md, ADR-004). Immutability is enforced in the database with triggers, not just by convention.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from retail_intel.domain.audit import AuditEvent, GENESIS_HASH
from retail_intel.domain.observations import (CollectionMethod, Observation, QualityFlag, canonical_json, sha256_hex)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
  content_hash TEXT PRIMARY KEY, media_type TEXT NOT NULL, content BLOB NOT NULL, stored_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observation (
  observation_id TEXT PRIMARY KEY, kind TEXT NOT NULL, tenant_id TEXT NOT NULL, source_id TEXT NOT NULL,
  competitor_id TEXT NOT NULL, listing_id TEXT NOT NULL, region TEXT NOT NULL, currency TEXT,
  observed_at TEXT NOT NULL, retrieved_at TEXT NOT NULL, payload_hash TEXT NOT NULL,
  is_demo INTEGER NOT NULL, quarantined INTEGER NOT NULL, body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_obs_listing ON observation (tenant_id, competitor_id, listing_id, kind, observed_at);
CREATE INDEX IF NOT EXISTS ix_obs_retrieved ON observation (retrieved_at);
CREATE TABLE IF NOT EXISTS recommendation (
  recommendation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_event (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, entity_id TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_event (entity_id);
"""

_IMMUTABLE = ["evidence", "observation", "audit_event"]


def _ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("Naive datetimes are rejected; supply timezone-aware timestamps")
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


class ObservationStore:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            for t in _IMMUTABLE:
                for op in ("UPDATE", "DELETE"):
                    self._conn.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
                        f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END")

    def close(self) -> None:
        self._conn.close()

    # ---- evidence (content-addressed, immutable) -------------------------------------------------------------
    def put_evidence(self, content: bytes | str | Dict[str, Any], media_type: str = "application/json") -> Tuple[str, str]:
        raw = content if isinstance(content, bytes) else (content if isinstance(content, str) else canonical_json(content)).encode("utf-8")
        h = sha256_hex(raw)
        with self._lock:
            self._conn.execute("INSERT OR IGNORE INTO evidence VALUES (?,?,?,?)",
                               (h, media_type, raw, _ts(datetime.now(timezone.utc))))
        return f"evidence://sha256/{h}", h

    def get_evidence(self, content_hash: str) -> Optional[bytes]:
        with self._lock:
            row = self._conn.execute("SELECT content FROM evidence WHERE content_hash=?", (content_hash,)).fetchone()
        return bytes(row[0]) if row else None

    # ---- observations ----------------------------------------------------------------------------------------
    def append_observation(self, obs: Observation) -> bool:
        """Insert an observation. Returns False if an identical observation (same ID) already exists."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (obs.observation_id, obs.kind, obs.provenance.tenant_id, obs.provenance.source_id,
                 obs.provenance.competitor_id, obs.listing_id, obs.region, obs.currency, _ts(obs.observed_at),
                 _ts(obs.provenance.retrieved_at), obs.provenance.payload_hash,
                 int(obs.provenance.collection_method == CollectionMethod.DEMO_DATA),
                 int(QualityFlag.QUARANTINED in obs.quality_flags), obs.model_dump_json()))
            return cur.rowcount == 1

    def history(self, *, tenant_id: str, kind: str, listing_id: str, competitor_id: Optional[str] = None,
                region: Optional[str] = None, as_of: Optional[datetime] = None, since: Optional[datetime] = None,
                until: Optional[datetime] = None, include_quarantined: bool = False) -> List[Observation]:
        """Observations in observed_at order. `as_of` answers "what did we know at T" (retrieved_at <= T), which makes
        every historical query reproducible even after later corrections or late-arriving data."""
        q = "SELECT body FROM observation WHERE tenant_id=? AND kind=? AND listing_id=?"
        args: List[Any] = [tenant_id, kind, listing_id]
        for col, val in (("competitor_id", competitor_id), ("region", region)):
            if val is not None:
                q += f" AND {col}=?"
                args.append(val)
        if as_of is not None:
            q += " AND retrieved_at<=?"
            args.append(_ts(as_of))
        if since is not None:
            q += " AND observed_at>=?"
            args.append(_ts(since))
        if until is not None:
            q += " AND observed_at<=?"
            args.append(_ts(until))
        if not include_quarantined:
            q += " AND quarantined=0"
        q += " ORDER BY observed_at ASC, observation_id ASC"
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [Observation.model_validate_json(r[0]) for r in rows]

    def latest(self, **kw: Any) -> Optional[Observation]:
        h = self.history(**kw)
        return h[-1] if h else None

    def listing_ids(self, *, tenant_id: str, competitor_id: str, as_of: Optional[datetime] = None) -> List[str]:
        q, args = "SELECT DISTINCT listing_id FROM observation WHERE tenant_id=? AND competitor_id=? AND quarantined=0", [tenant_id, competitor_id]
        if as_of is not None:
            q += " AND retrieved_at<=?"
            args.append(_ts(as_of))
        with self._lock:
            return sorted(r[0] for r in self._conn.execute(q, args).fetchall())

    def count_observations(self, *, demo_only: Optional[bool] = None) -> int:
        q = "SELECT COUNT(*) FROM observation" + ("" if demo_only is None else f" WHERE is_demo={int(demo_only)}")
        with self._lock:
            return int(self._conn.execute(q).fetchone()[0])

    # ---- recommendations (mutable state, full history lives in the audit log) -----------------------------------
    def save_recommendation(self, rec_id: str, tenant_id: str, status: str, body_json: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO recommendation VALUES (?,?,?,?,?) ON CONFLICT(recommendation_id) DO UPDATE SET "
                "status=excluded.status, updated_at=excluded.updated_at, body=excluded.body",
                (rec_id, tenant_id, status, _ts(datetime.now(timezone.utc)), body_json))

    def load_recommendation(self, rec_id: str) -> Optional[str]:
        with self._lock:
            row = self._conn.execute("SELECT body FROM recommendation WHERE recommendation_id=?", (rec_id,)).fetchone()
        return row[0] if row else None

    def list_recommendations(self, tenant_id: str, status: Optional[str] = None) -> List[str]:
        q, args = "SELECT body FROM recommendation WHERE tenant_id=?", [tenant_id]
        if status:
            q += " AND status=?"
            args.append(status)
        with self._lock:
            return [r[0] for r in self._conn.execute(q + " ORDER BY recommendation_id", args).fetchall()]

    # ---- audit sink ---------------------------------------------------------------------------------------------
    def append(self, event: AuditEvent) -> None:
        """AuditSink protocol: append one audit event (append-only table)."""
        with self._lock:
            self._conn.execute("INSERT INTO audit_event (event_id, entity_id, hash, body) VALUES (?,?,?,?)",
                               (event.event_id, event.entity_id, event.hash, event.model_dump_json()))

    def all(self, entity_id: Optional[str] = None) -> List[AuditEvent]:
        q, args = "SELECT body FROM audit_event", []
        if entity_id:
            q += " WHERE entity_id=?"
            args.append(entity_id)
        with self._lock:
            return [AuditEvent.model_validate_json(r[0]) for r in self._conn.execute(q + " ORDER BY seq", args).fetchall()]

    def last_hash(self) -> str:
        with self._lock:
            row = self._conn.execute("SELECT hash FROM audit_event ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS_HASH
