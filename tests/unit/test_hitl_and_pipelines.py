"""Unit tests for HITL, LLMOps guardrails, Golden Benchmark Runner, StreamBroker, and Ingestion."""

import pytest
from retail_intel.hitl.review_queue import HITLReviewQueue, HITLDecision, HITLTaskStatus
from retail_intel.llmops.guardrails import LLMGuardrails
from retail_intel.llmops.golden_eval import GoldenBenchmarkRunner
from retail_intel.mlops.validation import DataContractValidator
from retail_intel.mlops.registry import ModelRegistry
from retail_intel.data_engineering.ingestion.ingestion_pipeline import IngestionPipeline, IngestionPayload
from retail_intel.data_engineering.stream.stream_broker import StreamBroker, StreamMessage


@pytest.mark.unit
def test_hitl_review_queue():
    queue = HITLReviewQueue()
    task = queue.enqueue_task(
        competitor_sku="COMP-ERR-01",
        internal_sku_candidate="INT-EL-001",
        tau_score=0.55,
        escalation_reason="Confidence below 0.65 threshold",
        agentic_evidence={"verdict": "CONTRADICTORY_LISTING"},
    )
    assert task.status == HITLTaskStatus.PENDING
    assert len(queue.get_pending_tasks()) == 1
    # Task ID must be uuid-based (no collision under concurrent use)
    assert task.task_id.startswith("hitl_")
    assert len(task.task_id) > 10  # uuid4 hex is 32 chars

    # Submit decision
    resolved = queue.submit_decision(HITLDecision(
        task_id=task.task_id,
        decision="APPROVE",
        analyst_notes="Verified physically identical",
    ))
    assert resolved.status == HITLTaskStatus.APPROVED
    assert resolved.analyst_decision == "APPROVE"
    assert len(queue.get_pending_tasks()) == 0
    stats = queue.get_queue_stats()
    assert stats["approved"] == 1


@pytest.mark.unit
def test_llm_guardrails_groundedness():
    source_facts = {
        "title": "AuraWave Pro Wireless Headphones",
        "anc": "Hybrid Active",
        "battery": "40 hours",
        "price": 299.99
    }
    grounded_reasoning = "The AuraWave headphones feature 40 hours battery and hybrid active anc at 299.99 price."
    audit = LLMGuardrails.audit_reasoning_groundedness(grounded_reasoning, source_facts)
    assert audit.is_safe is True
    assert audit.faithfulness_score >= 0.80
    assert audit.hallucination_rate <= 0.20


@pytest.mark.unit
def test_golden_benchmark_runner(base_data_dir):
    runner = GoldenBenchmarkRunner(base_data_dir / "golden_benchmark_set.json")
    benchmarks = runner.load_benchmarks()
    assert len(benchmarks) >= 8

    decisions = {b["competitor_sku"]: {"verdict": b["expected_match_type"], "target_sku": b["expected_target_sku"]} for b in benchmarks}
    report = runner.evaluate_decisions(decisions)
    assert report.total_benchmarks == len(benchmarks)
    assert report.passed_count == len(benchmarks)
    assert report.accuracy == 1.0


@pytest.mark.unit
def test_data_contract_validator():
    validator = DataContractValidator()
    records = [
        {"sku": "VAL-01", "title": "Good Item", "brand": "BrandA", "current_price": 49.99, "pack_size": 1},
        {"sku": "", "title": "Bad Item", "brand": "BrandB", "current_price": -10.0, "pack_size": 0},
    ]
    res = validator.validate_batch(records)
    assert res.is_valid is False
    assert res.validated_record_count == 1
    assert len(res.errors) >= 2


@pytest.mark.unit
def test_model_registry():
    registry = ModelRegistry()
    artifacts = registry.list_artifacts()
    assert len(artifacts) >= 3
    bi = registry.get_artifact("bi_encoder")
    assert bi is not None
    assert bi.status == "PRODUCTION"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_pipeline_batch(sample_competitor_items):
    pipeline = IngestionPipeline()
    events = await pipeline.run_batch(sample_competitor_items)
    assert len(events) == len(sample_competitor_items)
    assert pipeline.honeypots_intercepted >= 1
    assert pipeline.phantoms_intercepted >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_broker_backpressure():
    broker = StreamBroker(max_buffer_size=10)
    pub_id = await broker.publish_event("test.topic", {"event": "crawl_complete", "sku": "SKU-99"})
    assert pub_id.startswith("msg_")
    stats = broker.get_dlq_stats()
    assert stats["buffer_depth"] == 1

    async def failing_handler(payload):
        raise RuntimeError("Simulated network timeout")

    msg = StreamMessage(message_id="msg_test", topic="test.topic", payload={}, max_retries=2)
    success = await broker.process_with_retry(msg, failing_handler)
    assert success is False
    assert len(broker.dead_letter_queue) == 1
