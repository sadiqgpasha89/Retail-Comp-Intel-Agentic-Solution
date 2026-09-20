# Software Document Record (SDR): Retail Competitor Intelligence Platform

---

## 1. Codebase Structure & Module Inventory

```
Retail-Comp-Intel-Agentic-Solution/
├── src/
│   ├── core/
│   │   ├── config.py                  # Pydantic BaseSettings with .env overrides & thresholds
│   │   └── logging.py                 # Structured JSON structured logging with contextual bindings
│   ├── data_engineering/
│   │   ├── dataset_generator.py       # Large-scale dynamic synthetic catalog & observation engine
│   │   ├── feature_store/             # In-memory & vector embedding store (HNSW/cosine)
│   │   ├── ingestion/                 # Headless crawler ingestion & honeypot interception
│   │   ├── normalization/             # Multi-retailer schema normalization & GPC taxonomy mapping
│   │   └── stream/                    # Event streaming broker simulation (Pub/Sub / Kafka)
│   ├── datascience/
│   │   ├── tier1_rules/               # Deterministic GTIN-14 and hard brand boundary engine
│   │   ├── tier2_ml/                  # Bi-encoder ANN retriever & Cross-encoder semantic scorer
│   │   ├── recommendation_engine.py   # Executive Merchandising & Pricing Action Directive Engine
│   │   └── anomaly_detector.py        # Isolation Forest price anomaly & volatility scanner
│   ├── agents/
│   │   ├── supervisor.py              # Cognitive Plan-Execute-Reflect-Report coordinator
│   │   ├── matcher.py                 # Multimodal equivalence arbiter agent
│   │   ├── promo_agent.py             # Cart checkout & coupon simulation agent
│   │   ├── strategy_agent.py          # Causal intent & elasticity modeling agent
│   │   ├── reflection_guard.py        # 4-Tier Hierarchy of Truth audit guardrail
│   │   ├── graph/                     # NetworkX & Spanner Graph Retail Property Knowledge Graph
│   │   └── tools/                     # Sandboxed agent tool registry
│   ├── hitl/
│   │   └── review_queue.py            # Merchandiser escalation & active feedback loop queue
│   ├── mlops/
│   │   └── drift_radar.py             # Population Stability Index (PSI), Wasserstein & Page-Hinkley
│   ├── metrics/
│   │   └── engine.py                  # 5-Plane Telemetry aggregator (Business, Agent, LLM, ML, Infra)
│   ├── api/
│   │   ├── main.py                    # FastAPI application lifespan & middleware
│   │   ├── schemas.py                 # Pydantic request/response validation schemas
│   │   └── routes/
│   │       ├── intelligence.py        # Single SKU resolution & SSE streaming endpoint
│   │       ├── recommendations.py     # Executive Merchandising Action Directives API
│   │       ├── catalog.py             # Internal & Competitor catalog query API
│   │       ├── graph.py               # 3D/2D Knowledge graph export API
│   │       ├── metrics.py             # 5-Plane telemetry metrics API
│   │       ├── drift.py               # Statistical drift radar API
│   │       ├── hitl.py                # HITL task management API
│   │       ├── pipelines.py           # Dataset generation & full lifecycle orchestration API
│   │       └── chaos.py               # Chaos engineering perturbation injection API
│   └── frontend/
│       ├── templates/index.html       # Single-page glassmorphic UI template
│       └── static/
│           ├── css/styles.css         # Luxury glassmorphic dark-mode styling system
│           └── js/app.js              # Three.js 3D WebGL graph, SSE streaming, & UI controller
├── tests/
│   ├── unit/                          # Unit tests for rules, ML, drift, feature store, recommendations
│   ├── integration/                   # Pipeline flow and API endpoint integration tests
│   ├── edge_case/                     # Validation of all 8 documented edge cases
│   └── performance/                   # Latency and throughput benchmarks
└── pyproject.toml                     # Python dependency management & configuration
```

---

## 2. Core Service Classes & Lifespan

### 2.1 ApplicationState (`src/api/main.py`)
Maintains global application context across the asynchronous server lifespan:
- `internal_records`: List of normalized internal products indexed by GTIN and SKU.
- `rule_engine`: `DeterministicRuleEngine` containing in-memory Modulo-10 GTIN indices.
- `feature_store`: `FeatureStore` containing 64-dimensional multimodal vector embeddings.
- `supervisor`: `SupervisorAgent` orchestrating the multi-agent cognitive mesh.
- `drift_radar`: `DriftRadar` evaluating continuous batch statistics.
- `metrics_engine`: `MetricsEngine` aggregating the 5 operational telemetry planes.

---

## 3. Algorithmic Formulations

### 3.1 Multimodal Embedding Similarity
Multimodal embedding scores combine textual semantics, visual attributes, and tabular specifications:
$$\text{Sim}_{\text{Total}}(x_{\text{comp}}, x_{\text{int}}) = \alpha \cdot \text{Sim}_{\text{Text}}(e_t^c, e_t^i) + \beta \cdot \text{Sim}_{\text{Vis}}(e_v^c, e_v^i) + \gamma \cdot \text{Sim}_{\text{Attr}}(a^c, a^i)$$
Where $\alpha + \beta + \gamma = 1.0$, dynamically calibrated per product category (e.g. higher $\beta$ visual weight for Apparel, higher $\gamma$ attribute weight for Power Tools).

### 3.2 Cross-Price Elasticity of Demand ($\varepsilon_{ij}$)
$$\varepsilon_{ij} = \frac{\% \Delta Q_i}{\% \Delta P_j} = \frac{(Q_i^{\text{new}} - Q_i^{\text{old}}) / Q_i^{\text{old}}}{(P_j^{\text{new}} - P_j^{\text{old}}) / P_j^{\text{old}}}$$
- High cross-elasticity ($\varepsilon_{ij} < -1.2$): Requires automated volume repricing defense.
- Low cross-elasticity ($\varepsilon_{ij} > -0.5$): Suggests margin hold and store-brand positioning.

---

## 4. Complete REST & SSE API Specifications

| Method | Endpoint | Description | Response Schema |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | System liveness probe & catalog sizes | `HealthResponse` |
| `GET` | `/api/v1/recommendations` | Strategic Merchandising Action Directives | `RecommendationsSummary` |
| `GET` | `/api/v1/recommendations/summary`| Top-level C-Suite financial KPIs | `JSON` |
| `POST`| `/api/v1/intelligence/analyze` | Single-SKU Tri-Tier Resolution | `AnalysisResponse` |
| `GET` | `/api/v1/intelligence/stream` | Server-Sent Events (SSE) Agent Trace | `text/event-stream` |
| `GET` | `/api/v1/catalog/competitor` | 48-competitor market catalog | `List[CompetitorItem]` |
| `GET` | `/api/v1/catalog/internal` | Internal product catalog | `List[InternalItem]` |
| `GET` | `/api/v1/graph/subgraph` | 3D/2D Knowledge Graph nodes & links | `GraphData` |
| `POST`| `/api/v1/pipelines/run-full-lifecycle` | Runs complete 6-stage pipeline (20k pts) | `PipelineLifecycleResponse` |
| `POST`| `/api/v1/pipelines/generate-dataset`| Synthesizes 20k–50k data points | `JSON` |
| `POST`| `/api/v1/pipelines/run-eval` | Executes Golden Benchmark evaluation | `BenchmarkRunReport` |
| `GET` | `/api/v1/metrics` | 5-Plane operational telemetry metrics | `MetricsPlaneReport` |
| `GET` | `/api/v1/drift` | Statistical drift radar scores (PSI/EMD) | `DriftReport` |
| `GET` | `/api/v1/hitl/queue` | Pending human review tasks | `HITLQueueResponse` |
| `POST`| `/api/v1/hitl/resolve/{task_id}`| Submits merchandiser arbitration decision | `JSON` |
| `POST`| `/api/v1/chaos/inject` | Injects synthetic attack perturbation | `ChaosStatus` |
| `POST`| `/api/v1/chaos/reset` | Resets active chaos perturbations | `ChaosStatus` |
