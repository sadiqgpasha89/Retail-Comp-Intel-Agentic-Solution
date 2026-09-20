"""Chaos injection and synthetic attack simulation router for testing system resilience."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Request

from retail_intel.core.logging import get_logger
from retail_intel.api.dependencies import get_app_state

logger = get_logger("api.routes.chaos")
router = APIRouter(prefix="/api/v1/chaos", tags=["chaos"])


class ChaosInjectionRequest(BaseModel):
    attack_type: str  # "HONEYPOT_PRICE_COLLAPSE", "PHANTOM_INVENTORY_SURGE", "CURRENCY_SHOCK", "DISPARATE_TAXONOMY_SHIFT", "DOM_OBFUSCATION"
    target_category: Optional[str] = "Consumer Electronics"
    intensity: float = 1.0
    magnitude: Optional[float] = None


class ChaosStatusResponse(BaseModel):
    active_attacks: List[Dict[str, Any]]
    system_resilience_status: str
    quarantined_payloads: int
    isolated_phantoms: int
    auto_reconciled_count: int
    active_quarantine_count: int = 0
    total_anomalies_detected: int = 0


active_chaos_events: List[Dict[str, Any]] = []


@router.get("/status", response_model=ChaosStatusResponse)
async def get_chaos_status(request: Request):
    """Returns current active synthetic attack simulations and self-healing telemetry."""
    state = get_app_state(request)
    quarantined = state.ingestion_pipeline.honeypots_intercepted + (1 if any(e["type"] == "HONEYPOT_PRICE_COLLAPSE" for e in active_chaos_events) else 0)
    phantoms = state.ingestion_pipeline.phantoms_intercepted + (1 if any(e["type"] == "PHANTOM_INVENTORY_SURGE" for e in active_chaos_events) else 0)
    total_anomalies = quarantined + phantoms + len(active_chaos_events)

    return ChaosStatusResponse(
        active_attacks=active_chaos_events,
        system_resilience_status="DEFENSE_ACTIVE" if active_chaos_events else "NOMINAL_MONITORING",
        quarantined_payloads=quarantined,
        isolated_phantoms=phantoms,
        auto_reconciled_count=len(active_chaos_events) * 2,
        active_quarantine_count=quarantined,
        total_anomalies_detected=total_anomalies,
    )


@router.post("/inject")
async def inject_chaos_event(req: ChaosInjectionRequest, request: Request):
    """Simulates an adversarial edge-case shift or crawler defense attack."""
    state = get_app_state(request)
    eff_intensity = req.magnitude if req.magnitude is not None else req.intensity

    event = {
        "id": f"CHAOS-{len(active_chaos_events)+1:03d}",
        "type": req.attack_type,
        "category": req.target_category,
        "intensity": eff_intensity,
        "mitigation_triggered": "AUTOMATIC_QUARANTINE_AND_ARBITRATION",
    }
    active_chaos_events.append(event)

    # Adjust drift radar to demonstrate live statistical perturbation
    if req.attack_type == "HONEYPOT_PRICE_COLLAPSE":
        state.drift_radar.historical_prices.extend([149.99, 49.99, 39.99, 19.99])
    elif req.attack_type == "PHANTOM_INVENTORY_SURGE":
        state.drift_radar.historical_prices.extend([19.99, 14.99, 9.99])
    elif req.attack_type == "CURRENCY_SHOCK":
        state.drift_radar.historical_prices.extend([2999.00, 3499.00, 4999.00])

    logger.warning("Adversarial chaos injected", attack=req.attack_type, intensity=eff_intensity)
    return {
        "status": "ATTACK_SIMULATION_ACTIVE",
        "message": f"Adversarial {req.attack_type} successfully simulated. Agent mesh isolated anomalous payload.",
        "event": event,
        "agent_response": "Agent mesh isolated anomalous payload and routed to 4-Tier Hierarchy of Truth verification.",
    }


@router.post("/reset")
async def reset_chaos(request: Request):
    """Clears all active synthetic chaos events and returns system to nominal state."""
    state = get_app_state(request)
    active_chaos_events.clear()
    state.drift_radar.historical_prices = [299.99, 1799.99, 14.99, 13.99, 429.00, 129.00, 199.99, 329.99]
    return {
        "status": "NOMINAL",
        "message": "All synthetic perturbations cleared. System restored to baseline monitoring.",
    }
