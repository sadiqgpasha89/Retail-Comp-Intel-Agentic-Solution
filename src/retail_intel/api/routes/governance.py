"""Governance routes: audit trail, source registry, listing import and as-of observation history.

These expose the domain layer (``retail_intel.domain``). Nothing here scrapes or contacts a competitor:
data enters only through an explicit upload against a registered, compliance-checked source.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from retail_intel.api.dependencies import get_app_state
from retail_intel.core.config import settings
from retail_intel.core.logging import get_logger
from retail_intel.domain.sources import (
    ComplianceError,
    CompetitorSource,
    ComplianceGate,
    import_listings,
)

logger = get_logger("api.routes.governance")
router = APIRouter(prefix="/api/v1", tags=["governance"])

MAX_IMPORT_BYTES = 5 * 1024 * 1024


class ImportSummary(BaseModel):
    run_id: str
    payload_hash: str
    rows_total: int
    observations_stored: int
    observations_duplicate: int
    rejected: List[Dict[str, Any]]
    quarantined_rows: List[int]
    source_id: str
    note: str = "Rejected rows are reported, never silently repaired; quarantined rows are stored but excluded from decisions."


@router.get("/audit")
async def list_audit(request: Request, entity_id: Optional[str] = None, limit: int = Query(200, ge=1, le=2000)):
    """Hash-chained audit events (newest last)."""
    state = get_app_state(request)
    events = state.audit_log.events(entity_id)
    return [e.model_dump(mode="json") for e in events[-limit:]]


@router.get("/audit/verify")
async def verify_audit(request: Request):
    """Recomputes the hash chain; `intact=false` means an event was altered, removed or reordered."""
    state = get_app_state(request)
    return {"intact": state.audit_log.verify(), "events": len(state.audit_log.events())}


@router.get("/sources")
async def list_sources(request: Request, active_only: bool = False):
    state = get_app_state(request)
    if active_only:
        return [s.model_dump(mode="json") for s in state.source_registry.list_active(ComplianceGate())]
    return [s.model_dump(mode="json") for s in state.source_registry.list_all()]


@router.put("/sources/{source_id}")
async def upsert_source(source_id: str, source: CompetitorSource, request: Request):
    """Registers a source. Permission is NOT assumed: `policy.permitted` must be set to true with a documented
    `basis`, otherwise the compliance gate refuses every read from it."""
    if source.source_id != source_id:
        raise HTTPException(status_code=400, detail="source_id in path and body must match")
    state = get_app_state(request)
    state.source_registry.upsert(source)
    state.audit_log.record("api", "source_upsert", "source", source_id,
                           {"type": source.source_type.value, "permitted": source.policy.permitted})
    return source.model_dump(mode="json")


@router.post("/imports", response_model=ImportSummary)
async def import_listing_file(request: Request, source_id: str = Query(...), fmt: str = Query(..., pattern="^(csv|json)$")):
    """Import a CSV/JSON listing file (raw request body) for a registered source."""
    state = get_app_state(request)
    source = state.source_registry.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Unknown source '{source_id}'")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")
    if len(body) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail=f"Import exceeds {MAX_IMPORT_BYTES} bytes")
    run_id = f"imp_{uuid.uuid4().hex[:12]}"
    gate = ComplianceGate()
    try:
        gate.assert_allowed(source, "read_listing")     # check permission before retaining anything
        evidence_uri, _ = state.observations.put_evidence(body, "text/csv" if fmt == "csv" else "application/json")
        result = import_listings(body, fmt, source, tenant_id=settings.tenant_id, run_id=run_id,
                                 evidence_uri=evidence_uri, gate=gate)
    except ComplianceError as e:
        state.audit_log.record("api", "import_refused", "source", source_id, {"reason": str(e)})
        raise HTTPException(status_code=403, detail=str(e))
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Unparseable file: {e}")

    stored = sum(1 for o in result.observations if state.observations.append_observation(o))
    state.audit_log.record("api", "import", "source", source_id,
                           {"run_id": run_id, "payload_hash": result.payload_hash, "rows": result.rows_total,
                            "stored": stored, "rejected": len(result.rejected)})
    return ImportSummary(
        run_id=run_id, payload_hash=result.payload_hash, rows_total=result.rows_total,
        observations_stored=stored, observations_duplicate=len(result.observations) - stored,
        rejected=[r.model_dump() for r in result.rejected], quarantined_rows=result.quarantined_rows,
        source_id=source_id,
    )


@router.get("/observations/history")
async def observation_history(
    request: Request,
    kind: str = Query(..., pattern="^(price|availability|promotion)$"),
    listing_id: str = Query(...),
    competitor_id: Optional[str] = None,
    region: Optional[str] = None,
    as_of: Optional[datetime] = Query(None, description="Only observations *retrieved* at or before this instant"),
    include_quarantined: bool = False,
):
    """Immutable observation history; `as_of` reproduces what was known at that time."""
    state = get_app_state(request)
    obs = state.observations.history(
        tenant_id=settings.tenant_id, kind=kind, listing_id=listing_id, competitor_id=competitor_id,
        region=region, as_of=as_of, include_quarantined=include_quarantined,
    )
    return [o.model_dump(mode="json") for o in obs]
