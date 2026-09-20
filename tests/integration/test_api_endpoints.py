"""Integration tests for FastAPI endpoints."""

import pytest


@pytest.mark.integration
def test_health_check(test_client):
    res = test_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["internal_catalog_size"] > 0
    assert data["competitor_catalog_size"] > 0


@pytest.mark.integration
def test_catalog_endpoints(test_client):
    res_int = test_client.get("/api/v1/catalog/internal")
    assert res_int.status_code == 200
    assert len(res_int.json()) >= 8

    res_comp = test_client.get("/api/v1/catalog/competitor")
    assert res_comp.status_code == 200
    assert len(res_comp.json()) >= 8


@pytest.mark.integration
def test_intelligence_analyze_exact_match(test_client):
    res = test_client.post("/api/v1/intelligence/analyze", json={"competitor_sku": "APX-AURA-99"})
    assert res.status_code == 200
    data = res.json()
    assert data["resolution_tier"] == "TIER_1_DETERMINISTIC"
    assert data["verdict"] == "EXACT_MATCH"
    assert data["target_internal_sku"] == "INT-EL-001"


@pytest.mark.integration
def test_intelligence_analyze_agentic_flow(test_client):
    res = test_client.post("/api/v1/intelligence/analyze", json={"competitor_sku": "NOV-CHAIR-ERGOPRO"})
    assert res.status_code == 200
    data = res.json()
    assert data["resolution_tier"] == "TIER_3_AGENTIC"
    assert data["verdict"] == "EQUIVALENT_PRIVATE_LABEL"
    assert data["target_internal_sku"] == "INT-HOME-201"
    assert data["agentic_intelligence"] is not None


@pytest.mark.integration
def test_metrics_endpoint(test_client):
    res = test_client.get("/api/v1/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "business" in data
    assert "agentic" in data
    assert "rag_quality" in data
    assert "ml_system" in data
    assert "infrastructure" in data


@pytest.mark.integration
def test_drift_endpoint(test_client):
    res = test_client.get("/api/v1/drift")
    assert res.status_code == 200
    data = res.json()
    assert "psi_score" in data
    assert "wasserstein_embedding_distance" in data


@pytest.mark.integration
def test_graph_endpoint(test_client):
    res = test_client.get("/api/v1/graph/subgraph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) > 0


@pytest.mark.integration
def test_recommendations_endpoints(test_client):
    # Test GET /api/v1/recommendations
    res = test_client.get("/api/v1/recommendations")
    assert res.status_code == 200
    data = res.json()
    assert "total_active_recommendations" in data
    assert "gross_margin_protected_usd" in data
    assert len(data["top_actions"]) > 0

    # Test GET /api/v1/recommendations/summary
    res_summary = test_client.get("/api/v1/recommendations/summary")
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert "revenue_at_risk_usd" in summary_data
    assert "gross_margin_protected_usd" in summary_data

    # Test POST /api/v1/recommendations/orchestrate
    res_orch = test_client.post(
        "/api/v1/recommendations/orchestrate",
        json={"competitor_sku": "ZEN-TV-65-OLED"}
    )
    assert res_orch.status_code == 200
    orch_data = res_orch.json()
    assert orch_data["status"] == "ORCHESTRATED"
    assert "causal_intent" in orch_data
    assert "directive_action" in orch_data

    # Test POST /api/v1/recommendations/approve
    res_appr = test_client.post(
        "/api/v1/recommendations/approve",
        json={
            "recommendation_id": "REC-0001",
            "action_type": "AUTO_REPRICE_VOLUME_DEFENSE",
            "target_sku": "INT-EL-002",
            "approved_price": 1599.00
        }
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "APPROVED_AND_QUEUED"


@pytest.mark.integration
def test_chaos_endpoints(test_client):
    res_status = test_client.get("/api/v1/chaos/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert "system_resilience_status" in data

    res_inject = test_client.post(
        "/api/v1/chaos/inject",
        json={"attack_type": "HONEYPOT_PRICE_COLLAPSE", "intensity": 1.0}
    )
    assert res_inject.status_code == 200
    assert res_inject.json()["status"] == "ATTACK_SIMULATION_ACTIVE"

    res_reset = test_client.post("/api/v1/chaos/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "NOMINAL"


@pytest.mark.integration
def test_sse_streaming_endpoint(test_client):
    # Test both competitor_sku and sku query parameters
    res_comp = test_client.get("/api/v1/intelligence/stream?competitor_sku=ZEN-TV-65-OLED")
    assert res_comp.status_code == 200
    assert "text/event-stream" in res_comp.headers.get("content-type", "")
    assert "data: " in res_comp.text

    res_sku = test_client.get("/api/v1/intelligence/stream?sku=ZEN-TV-65-OLED")
    assert res_sku.status_code == 200
    assert "data: " in res_sku.text


@pytest.mark.integration
def test_full_pipeline_lifecycle(test_client):
    res = test_client.post("/api/v1/pipelines/run-full-lifecycle")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["total_datapoints_processed"] >= 1000
    assert data["active_recommendations_count"] > 0
    assert len(data["stages_completed"]) == 6
