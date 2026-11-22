# Capability Matrix

Maps every requirement in the implementation plan to what the repository actually contains. It is the honest baseline for the other documents: if a capability is not `implemented` here, the BRD/FSD/TSD describe it as a target, not a fact.

**Status key**

| Status | Meaning |
|---|---|
| `implemented` | Real code, exercised by tests that run and pass |
| `partial` | Real code exists but is not wired end to end, or covers only part of the requirement |
| `mocked` | Behaviour is simulated or uses synthetic/hardcoded inputs; it demonstrates a flow but proves nothing about real data |
| `missing` | Not present. Listed in the backlog |

**Verification basis.** Counts below were produced in a sandbox without network access (see [Test evidence](#test-evidence)). The HTTP-level integration tests and the real `fastapi` / `structlog` / `pydantic-settings` packages could **not** be exercised there, so API behaviour is verified at route-handler level only.

**Data caveat.** All catalogue and competitor data in `data/` is synthetic. The LLM layer is simulated unless a provider is configured. Nothing is scraped.

---

## 2.1 Competitor and source management

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Competitor/source registry (merchant, domain, region, currency, channel, type, priority, schedule) | partial | `domain/sources.py` `CompetitorSource`, `SourceRegistry`; `PUT/GET /api/v1/sources`; `tests/unit/domain/test_sources_and_safety.py` | In-memory only; not persisted across restarts (B-02). `schedule_cron` is stored but nothing executes it |
| Source preference order (API, feed, licensed, public) | implemented | `SOURCE_PREFERENCE`, `list_active` ordering | Ordering only; no adapters other than import |
| Compliance gate: permission basis, revocation, never-permitted actions | implemented | `ComplianceGate`, `NEVER_PERMITTED_ACTIONS`; tests refuse unpermitted, revoked and never-permitted actions | Gate is enforced on import; no live adapter exists to enforce it on |
| Rate limiting, retry/backoff | implemented (library) | `TokenBucket`, `retry_with_backoff`, tests | Not used by a live collector because there is none (B-03) |
| Source health and freshness SLA | implemented (library) | `SourceHealth.record_run/is_stale`, tests | Not exposed via API; no alerting (B-07) |
| Scheduled and on-demand collection, pagination, incremental refresh | missing | none | No scheduler or worker (B-03) |
| Real permitted source adapter | missing | none | CSV/JSON import is the only real ingestion path (B-04) |
| Provenance per observation (method, URL, retrieval time, parser version, payload hash, evidence ref) | implemented | `domain/observations.py` `Provenance`; `ObservationStore.put_evidence`; tests | `source_url` is not populated by the importer |
| CSV/JSON upload with reject/quarantine | implemented | `import_listings`, `POST /api/v1/imports`; `tests/unit/domain/test_sources_and_safety.py`, `test_governed_api_handlers.py` | 5 MB request cap; no multipart UI |
| Sample/demo data | implemented | `data/*.json`, `data_engineering/dataset_generator.py` | Synthetic; flagged `DEMO_DATA` |

## 2.2 Catalogue and assortment intelligence

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Ingest internal master and competitor listings | partial | `/api/v1/catalog/*`, startup loader in `api/main.py` | Loads bundled JSON only; no import API for the internal master (B-06) |
| Identifier/attribute capture | implemented | `normalization_pipeline.py` `NormalizedProductRecord` | Source values preserved in `raw_payload_ref` |
| Detect new/delisted listings | implemented (library) | `signals.new_and_delisted`, tests | Not surfaced in API/UI |
| Configurable taxonomy (GPC or tenant) | partial | GPC alignment in normalizer; `configs/category_weights.yaml` | Fixed mapping; no tenant taxonomy editor; weights file is not loaded by code (B-14) |
| Unit/pack/currency normalization, source values preserved | implemented | `domain/units.py`, `domain/pricing.py` `FxRates`; `test_matching_and_units.py` | FX rates are caller-supplied; no rate feed |
| Coverage and product-gap opportunities | implemented (library) | `signals.assortment_gaps`, `category_coverage`, `observed_share_of_assortment` | Not exposed via API |

## 2.3 Identity resolution and matching

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Tier 1 deterministic (GTIN checksum, exact keys, hard rules) | implemented | `datascience/tier1_rules/deterministic_engine.py`; `validate_gtin_checksum`; `test_deterministic_rules.py` | |
| Tier 2 ML: candidate retrieval + pair scoring | mocked | `tier2_ml/bi_encoder.py`, `cross_encoder.py`, `feature_store.py` | Deterministic hashed embeddings and a heuristic scorer, not trained models. No BM25 lexical retrieval (B-08). Thresholds 0.92/0.65/0.40 are universal, not calibrated per category |
| Tier 3 agentic arbitration | mocked | `agents/*`; LLM provider is simulated | Real provider path is configuration only; untested against a live model |
| Tier 4 human review queue | partial | `hitl/review_queue.py`, `/api/v1/hitl/*`; `test_hitl_and_pipelines.py` | In-memory; no reviewer identity/permissions; no demo seeding any more |
| 8 explicit match classes | partial | `domain/match_classes.py` `MatchClass`; tests | **The live `/intelligence/analyze` path still emits its legacy verdicts** (`EXACT_MATCH`, `DIRECT_SUBSTITUTE`, `EQUIVALENT_PRIVATE_LABEL`, `UNFULFILLED_PHANTOM`, `HONEYPOT_TRAP`, `CONTRADICTORY_LISTING`). The new classes are a tested library, not yet the pipeline output (B-09) |
| Hard-conflict guard (pack size, model, capacity, generation, bundle) | implemented (library) | `detect_hard_conflicts`, `guard_auto_match`; tests | Same wiring gap as above |
| Match decision record (evidence, tier, features, model version, override history) | partial | `MatchDecision`, `ReviewOverride` models | Not persisted; not produced by the pipeline (B-09) |
| Calibrate thresholds against a labelled benchmark by category | missing | none | 8-case golden set is far too small to calibrate (B-10) |
| Golden benchmark | partial | `data/golden_benchmark_set.json` (8 cases), `llmops/golden_eval.py`, `make eval` | **Measured live: 7/8.** The miss is `ZEN-TV-65-OLED` (expected `DIRECT_SUBSTITUTE`, got `EQUIVALENT_PRIVATE_LABEL`). Earlier docs reported 100% from scripted answers; that was an artefact and has been removed |

## 2.4 Price and promotion intelligence

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Track list/sale/unit/reference price, shipping | implemented | `price_values`, `Observation`; `test_pricing.py` | |
| Effective comparable price with transparent breakdown | implemented | `compute_effective_price` (Decimal), `EffectivePrice.breakdown`; 10 tests | Library; the live pipeline's `effective_price` still comes from the legacy normalizer |
| Offer mechanics: coupons, cart discounts, multi-buy, bundles, threshold, loyalty, payment offers | implemented | `OfferType`, `Condition`; tests cover each | Extraction of offers from raw pages is not implemented (importer accepts a structured `offers` column) |
| Conditional vs generally available prices | implemented | `Condition`, `assume_conditions`; tests | |
| Tax/shipping treatment explicit | implemented | `TaxTreatment`, `include_shipping` | |
| Price-change detection, discount depth/frequency, volatility, index | implemented (library) | `signals.py`; `test_store_and_signals.py` | Not exposed via API |
| Historical timelines with evidence, reproducible "as of" | implemented | `ObservationStore.history(as_of=...)`; `GET /api/v1/observations/history`; tests | |
| MAP/contract flag for human review (no accusations) | implemented | `PolicyEngine` `MAP_VIOLATION` blocks approval; promo flag renamed `requires_map_review` | MAP price must be supplied on the SKU context; the demo catalogue has none |

## 2.5 Inventory and availability

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| States: in/low/out/preorder/backorder/unknown, with delivery window recorded; unknown is not out-of-stock | implemented | `domain/availability.py`; `test_availability.py` | |
| Availability and delivery-promise change detection | implemented (library) | `detect_availability_change` | Not exposed via API |
| Phantom inventory as a hypothesis from repeated observations | implemented (library) | `phantom_inventory_hypothesis` (needs ≥2 samples) | The legacy tier-3 path still labels `UNFULFILLED_PHANTOM` from a single listing |
| No inferred competitor stock quantities | implemented | No code path computes one | |

## 2.6 Signals, analytics, strategy

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Statistical/ML anomaly detection with contributing features | partial | Isolation Forest in `tier2_ml/anomaly_detector.py`; `signals.robust_price_anomaly` (median/MAD) | Trained on synthetic data; contributing features not surfaced |
| Hypotheses labelled as hypotheses, alternatives, confidence | partial | `signals.hypothesize_price_move`; strategy agent wording and `causal_intent` docstring now say "hypothesis" | Legacy enum names (`PREDATORY_UNDERCUTTING`…) are kept for API compatibility |
| Financial impact only with sales/cost/elasticity inputs, ranges, assumptions | implemented | `estimate_margin_impact` returns ranges or `InsufficientInputs`; recommendations carry `estimate_gap` | The legacy engine's `financial_impact_usd` and agent margin figures use **assumed unit volumes** (named constants `ASSUMED_UNITS_*`) and are illustrative only |
| What-if scenarios | partial | Frontend elasticity simulator; `estimate_margin_impact` | Simulator is client-side, uses assumed elasticity |
| Recommended action vocabulary | implemented | `RecType` (monitor, investigate, hold, review, protect margin, evaluate promotion, source equivalent, escalate) | Legacy engine action names are mapped onto these |

## 2.7 Agentic assistant

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Natural-language query interface with citations and permission scoping | missing | none | (B-11). Agent streaming exists for per-SKU analysis only (`/intelligence/stream`) |

## 2.8 Alerts, reports, decision management

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Recommendation lifecycle proposed → reviewed → approved/rejected → actioned → measured, with expiry | implemented | `RecommendationWorkflow`; `/api/v1/recommendations/{id}/review\|approve\|reject\|execute\|outcome`; `test_recommendations.py`, `test_governed_api_handlers.py` | Roles come from a request header (demo identity, **not** authentication) |
| Owner, rationale, assumptions, approval, timestamp, expiry, outcome | implemented | `Recommendation`, `DecisionRecord` | |
| Immutable, hash-chained audit trail | implemented | `AuditLog`, `GET /api/v1/audit`, `/audit/verify`; SQLite append-only triggers; tests | Tamper-evident, not tamper-proof: someone with database write access to a non-triggered copy could rebuild the chain |
| Policy gates: margin floor, MAP, bounds, currency, region, stock | implemented | `PolicyEngine`; tests | Needs COGS/MAP in the SKU context; unknown COGS blocks approval by design |
| Dry-run, idempotency keys | implemented | `execute(dry_run=True)`; replay test | |
| Write integrations (repricer/ERP) | missing (by design) | `WriteIntegration` protocol only | `WRITES_ENABLED` defaults false and no integration ships (ADR-007) |
| Configurable alerts, routing, dedup, cooldown, acknowledgement | missing | none | (B-07) |
| Scheduled reports, CSV/XLSX/PDF export | missing | none | (B-13) |

## 2.9 Dashboard and UX

| View in plan | Status | Evidence |
|---|---|---|
| Executive overview | partial | "Causal War Room" tab; figures are demo data and some derive from assumed volumes |
| Competitor explorer | partial | Market Intelligence tab; no registry editor |
| Product comparison | partial | "Inspect" side-by-side |
| Pricing & promotions | partial | Effective price shown; no history chart wired to `observations/history` |
| Assortment intelligence | missing | library only |
| Inventory & fulfilment | missing | library only |
| Recommendations | partial | Cards plus policy-checked approve (dry-run); no outcomes view |
| Agent operations | partial | Multi-agent mesh, SSE thought stream, HITL queue |
| Administration | missing | no user/role/source UI |
| Accessibility audit | missing | frontend not audited |

## 3. Agent and decision architecture

| Component | Status | Evidence |
|---|---|---|
| Supervisor with typed state, step budget | partial | `agents/supervisor.py`, `agent_step_budget`, `agent_max_iterations`; no cancellation or time/cost budget |
| Matcher / Promo / Strategy / Reflection | mocked | `agents/*` with simulated LLM |
| Source/discovery worker, Availability verifier, Market-signal agent, Reporting assistant | missing as agents | Availability and signal logic exist as deterministic library code |
| Prompt-injection resistance | partial | `domain/safety.py` scan/quarantine/`wrap_for_llm`; **only the importer calls it** (suspicious rows quarantined). The agents do not yet wrap source text or call the scanner (B-18) |
| Decision policy: recommendations only by default | implemented | See 2.8 |

## 4. Workflow and 5. Data/storage

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Immutable raw evidence, content hash | implemented | `evidence` table, `put_evidence` | SQLite blob; no object storage provider (B-02) |
| Normalized observations, history not overwritten | implemented | append-only `observation` table with triggers; deterministic IDs make re-import idempotent | |
| Validate, deduplicate, quarantine | implemented | importer; tests | |
| Operational DB for config/decisions | partial | SQLite `recommendation`, `audit_event` | Sources, users, schedules not persisted |
| Analytical warehouse | missing | none | BigQuery appears in config only |
| Vector index | mocked | `FeatureStore` in-process | No persistence or versioned rebuild |
| Knowledge graph | partial | NetworkX in-process; evidence per edge not stored | |
| Tenant, user, role, permission entities | missing | `tenant_id` is a setting and a column; no tenant isolation | (B-01) |
| collection_run, collection_schedule, match_candidate, review_feedback, market_signal, agent_run, tool_execution, model_version tables | missing | none | |

## 6. Technical architecture

| Requirement | Status | Notes |
|---|---|---|
| FastAPI preserved, versioned routes | implemented | `/api/v1/*` |
| Async workers/queues for collection | missing | `StreamBroker` is in-process (B-03) |
| Local Docker dev | partial | `docker/` files updated; image build not run in the sandbox |
| Cloud profile | partial | `deploy/gcp` (Cloud Run + Artifact Registry) and `deploy/aws` (App Runner + ECR) terraform; **never applied or validated**. Pub/Sub, BigQuery, Spanner, Vertex AI are named in config but neither provisioned nor wired |
| Provider interfaces for storage/streaming/secrets | partial | `ExecutionMode` switch; no secrets-manager integration |
| Pinned dependencies | partial | Lower bounds in `pyproject.toml`; no lock file (B-15) |

## 8. Security and responsible use

| Requirement | Status | Notes |
|---|---|---|
| RBAC, tenant isolation, SSO/OIDC | missing | Role is a claimed header. Do not expose a deployment publicly (`allow_public_access` defaults to false in terraform) (B-01) |
| Secrets, encryption, key rotation | missing | Environment variables only |
| Redaction of secrets/PII in logs and LLM context | missing | |
| Untrusted-content handling | partial | Importer only; see section 3 |
| Allowlisted sources, never-permitted actions | implemented | See 2.1 |
| Retention/deletion policy | missing | Append-only store has no retention job |

## 9. MLOps / LLMOps

| Requirement | Status | Notes |
|---|---|---|
| Golden benchmark covering all listed challenge classes | partial | 8 cases cover a subset; no variants, bundles, false GTINs, taxonomy clashes at scale |
| Precision/recall/F1 per category and class; false-positive rate | missing | Only pass/fail accuracy is reported (B-10) |
| Drift monitoring | implemented | `mlops/drift_radar.py` PSI, Wasserstein, Page-Hinkley; the embedding distance is `None` until embeddings are supplied. PSI baseline is the bundled demo price list |
| Model registry | mocked | `mlops/registry.py` lists three demo artefacts with **no metrics** |
| LLM groundedness etc. | partial | `llmops/guardrails.py` token-overlap heuristic only; precision/recall are not computed |
| Metrics truthfulness | implemented | `metrics/engine.py` reports only measured values; unmeasured fields are omitted |
| Shadow/canary/rollback | missing | |

## 10. Non-functional

| Requirement | Status | Notes |
|---|---|---|
| Measured P50/P95/P99 and throughput | partial | P99 over recorded analyses only; `tests/performance` asserts loose bounds on demo data. **No production-scale claim is made** |
| Retries, DLQ, idempotency | partial | Stream broker retry/DLQ in-process; import and execute are idempotent |
| Resilience, backups, restore tests | missing | |
| Cost controls | missing | Deterministic-first routing exists; no budgets |

---

## Backlog (prioritised)

| ID | Item | Plan phase |
|---|---|---|
| B-01 | Auth: OIDC/SSO, real RBAC, tenant isolation, per-role route guards | 1, 6 |
| B-02 | Persist source registry and config; storage provider interfaces (object store, relational, analytical) | 1 |
| B-03 | Queue + workers + scheduler for collection runs, with run history and status API | 2 |
| B-04 | First real permitted source adapter (official API or partner feed) with contract tests | 2 |
| B-05 | Prometheus/OpenTelemetry metrics for multi-worker deployments | 6 |
| B-06 | Internal product master import endpoint with validation | 1 |
| B-07 | Alerts (thresholds, routing, dedup, cooldown, acknowledgement) and source-failure alerts | 5 |
| B-08 | BM25 lexical retrieval; trained bi/cross-encoder with versioned artefacts | 3 |
| B-09 | Route the live pipeline through `MatchClass`, the hard-conflict guard and persisted `MatchDecision` | 3 |
| B-10 | Larger labelled benchmark; per-category/class precision, recall, F1, false-positive rate; threshold calibration | 3, 9 |
| B-11 | Natural-language assistant over governed tools with citations | 5 |
| B-12 | Rolling price baseline for PSI instead of the bundled demo list | 3 |
| B-13 | Scheduled reports and CSV/XLSX/PDF export | 5 |
| B-14 | Load `configs/category_weights.yaml` (currently unused) or delete it | 3 |
| B-15 | Dependency lock file; CI running the full suite with real packages | 6 |
| B-16 | Wire the domain libraries (effective price, availability, signals) into the analysis path and UI | 3, 5 |
| B-18 | Apply `scan_untrusted_text`/`wrap_for_llm` to every text field the agents see; add tool-argument validation | 4, 8 |
| B-17 | Deployment validation, load tests, backup/restore drill, security review | 6 |

---

## Test evidence

Run in a network-less sandbox, with local import shims (kept outside the repository) standing in for `fastapi`, `structlog`, `pydantic_settings`, `starlette` and `tenacity`, plus an asyncio marker shim.

| Suite | Result | Notes |
|---|---|---|
| `tests/unit` (incl. `tests/unit/domain`) | **101 passed** | Domain layer 71 tests, plus 8 route-handler tests (handlers called directly) |
| `scripts/run_golden_eval.py` | **7/8 (87.5%)** | Live pipeline, no oracle; the one miss is named above |
| `ruff check --select F,E9` | clean | Full default ruleset reports many pre-existing style findings; not addressed |
| `tests/integration`, `tests/edge_case`, `tests/performance` | **not run** | Need `TestClient` and the real packages. Integration tests were updated for the new lifecycle but are unexecuted |
| Docker build, terraform, frontend in a browser | **not run** | |

Reproduce with real dependencies: `make install && make test`. Domain tests alone need only `pydantic`: `make test-domain`.
