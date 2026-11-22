# AURORA RETAIL INTEL: Enterprise User Guide & Operational Manual

---

## 1. Executive Overview

**AURORA RETAIL INTEL** is a four-tier hybrid retail competitor intelligence platform that recommends pricing and merchandising actions for human approval. This build runs on **synthetic demo data** (48 fictional competitors, 10 categories, up to 20,000 generated data points) with a **simulated** agent layer. It does not scrape live sites and it does not change prices anywhere. See the [capability matrix](CAPABILITY_MATRIX.md) for what is real, partial, simulated or missing.

---

## 2. Navigating the Dual-Mode Interface

The platform provides a dual-mode interface designed for distinct personas:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  👔 Executive Stakeholder View (Default - C-Suite & VP Merchandising)       │
│  ├─ 1. Executive Causal War Room & ROI Overview                             │
│  ├─ 2. Strategic Recommendations (Commercial Merchandising Actions)         │
│  ├─ 3. Market Intelligence & Product Explorer (48 Competitors)              │
│  └─ 4. 3D & 2D Retail Property Knowledge Graph                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ⚙️ System & MLOps Telemetry Hub (Architecture, Engineering & Data Science) │
│  ├─ A. 6-Stage Operational Architecture Lifecycle                           │
│  ├─ B. Multi-Agent Streaming Mesh (Plan-Execute-Reflect-Report SSE)         │
│  ├─ C. 5-Plane Enterprise Telemetry & Statistical Drift Radar               │
│  ├─ D. Cloud Architecture (Google Cloud Platform vs AWS Bedrock)            │
│  ├─ E. 8 Critical Edge Cases & Chaos Engineering Sandbox                    │
│  └─ F. 20,000+ Dataset Studio & Golden Evaluation Benchmark                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Executive Stakeholder Features

### 3.1 📊 Executive Causal War Room
- **Hero ROI Metrics**:
  - **Gross Margin Protected**: Total financial value preserved by intercepting unfulfillable phantom inventory and honeypot traps before algorithmic price erosion.
  - **Projected Revenue Uplift**: Incremental revenue unlocked through targeted volume repricing and OEM store-brand arbitrage.
  - **Market Assortment Coverage**: Proportion of competitor catalog footprint harmonized to our canonical GPC taxonomy.
  - **Portfolio Price Index (PI)**: Aggregate ratio of competitor price to internal price (Benchmark: 98.0 – 102.0).
- **Interactive Cross-Price Elasticity Simulator**:
  1. Use the **Competitor Price Cut Slider** (-0% to -40%) to simulate rival price drops.
  2. Toggle between **Strategy A (Aggressive Price Match)** and **Strategy B (Hold Margin & Protect Brand)**.
  3. Observe real-time weekly revenue impact vs gross margin preservation.
- **Active Market Catalog Feed**:
  - Real-time table streaming scraped items across 48 competitors.
  - Filter by category (*Consumer Electronics, Home & Living, Apparel, Grocery, etc.*).
  - Click **"Inspect →"** on any SKU to launch the side-by-side Multimodal Product Inspector.

---

### 3.2 💡 Strategic Merchandising Recommendations
Actionable commercial directives formulated using retail merchandising business logic:

1. **Auto-Reprice Volume Defense**:
   - *Trigger*: Competitor undercuts price on high-velocity, elastic SKU where margin headroom remains above cost floor.
   - *Action*: Commit dynamic price adjustment to defend monthly category market share.
2. **Hold Margin & Phantom Defense**:
   - *Trigger*: Competitor advertises an aggressive price on a backordered (>30d) or unfulfillable phantom lure.
   - *Action*: Lock SKU against automated algorithmic matching, preserving gross margin.
3. **Enforce MAP Policy Violation**:
   - *Trigger*: Competitor advertised price drops below contractual Minimum Advertised Price (MAP).
   - *Action*: Flag for **human compliance review** with the supporting observations. The system never contacts the merchant or sends notices.
4. **OEM Store-Brand Arbitrage**:
   - *Trigger*: Knowledge Graph detects competitor private label sharing the identical OEM factory and patent.
   - *Action*: Highlight physical equivalency on product pages to capture switchers at +48% gross margins.
5. **Basket Builder Cross-Sell**:
   - *Trigger*: Core product price parity with high-margin attached accessory opportunity.
   - *Action*: Bundle accessory at 65% gross margin to expand Average Order Value (AOV).

---

### 3.3 🔍 Market Intelligence & Four-Tier Resolution Console
- **Four-Tier Decision Split**:
  - **Tier 1 (Deterministic Rules, τ = 1.0)**: Exact barcode / GTIN-14 matches and hard brand filters.
  - **Tier 2 (Classical ML, τ ≥ 0.92)**: Bi-encoder ANN retrieval and Cross-encoder semantic re-ranking.
  - **Tier 3 (Multi-Agent Cognitive Arbiter, 0.65 ≤ τ < 0.92)**: LLM supervisor orchestrating Promo, Matcher, and Strategy agents.
  - **Tier 4 (Human-in-the-Loop Gatekeeper, τ < 0.65 or Clash)**: Escalated to merchandiser queue.
- **Multimodal SKU Comparison Card**:
  - Side-by-side view comparing competitor listing against internal catalog product (Specs, MSRP, COGS, Coupons, and OEM links).

---

### 3.4 🕸️ 3D & 2D Retail Knowledge Graph Explorer
- **3D WebGL Constellation (Three.js)**:
  - **Orbit & Rotate**: Click and drag to rotate the 3D graph in space.
  - **Deep Zoom**: Scroll mouse wheel or click **[Zoom +] / [Zoom -]** buttons.
  - **Instant Search & Focus**: Type any SKU, OEM Factory, or Brand into the search box to automatically fly the 3D camera to the node.
  - **Entity Inspector**: Displays detailed supplier relationships, factory locations, and patent links.
- **2D Top-Down Mode**: Toggle to the 2D Interactive Map for classic planar navigation.

---

## 4. Engineering & MLOps Telemetry Hub

### 4.1 🔄 6-Stage Operational Lifecycle
1. **Perimeter Discovery**: Automated domain mapping across 48 competitors and marketplace sub-stores.
2. **Multimodal Ingestion**: DOM harvesting, viewport screenshots, and cart checkout simulation.
3. **Entity Resolution**: Universal GPC projection and multimodal vector embedding synthesis.
4. **Signal & Anomaly Detection**: Share-of-shelf rank tracking, coupon clipping, and isolation forest scans.
5. **Causal Synthesis**: ReAct hypothesis testing (Predatory vs Liquidation vs Phantom).
6. **Recommendation workflow**: review, policy-checked approval and dry-run execution. No repricer or ERP integration exists; downstream writes are disabled.

---

### 4.2 🤖 Multi-Agent Execution Mesh (P-E-R-R)
- **Plan-Execute-Reflect-Report Loop**:
  - Select any challenge SKU (e.g. `ZEN-TV-65-OLED` or `NOV-CHAIR-ERGOPRO`).
  - Click **"Stream Thoughts"** to observe real-time Server-Sent Events (SSE).
- **4-Tier Hierarchy of Truth Guardrail**:
  1. *Tier 1*: Customer Review Photos (Ground Truth)
  2. *Tier 2*: Manufacturer Spec Tables & GTIN Barcodes
  3. *Tier 3*: High-Res PDP Hero Imagery
  4. *Tier 4*: Textual Marketing Titles & Taglines

---

### 4.3 📊 5-Plane Telemetry & Statistical Drift Radar
- **5 Operational Planes**: Business Plane, Agentic Plane, LLM/RAG Quality Plane, Classical ML Plane, Infra Plane.
- **Drift Telemetry**:
  - **PSI (Population Stability Index)**: Ingestion covariate shift monitoring (Alert at PSI > 0.10).
  - **Wasserstein Distance**: Earth Mover's Distance tracking embedding cluster drift.
  - **Page-Hinkley Test**: Sequential statistical test detecting residual concept decay.

---

### 4.4 ⚡ 8 Edge Cases & Chaos Sandbox
- Click **"Test Scenario"** on any of the 8 documented edge cases (*Honeypots, Deceptive 3-Packs, OEM Clones, Hidden Cart Vouchers, Phantom Stock, Taxonomy Clashes, Spot FX Volatility, Multimodal Mismatches*).
- Inject live perturbations (*Honeypot Price Collapse, Phantom Inventory Surge, Currency Shock*) to verify system resilience.

---

## 5. 1-Click Operations

### ▶ Run Full Pipeline
Click the glowing **"Run Full Pipeline"** button in the top navigation header:
1. Re-indexes 20,000+ data points across 48 competitors and 10 categories.
2. Rebuilds the deterministic GTIN index and HNSW vector store.
3. Syncs the 3D Knowledge Graph relationships.
4. Formulates fresh C-Suite Merchandising Action Directives.
5. Displays a live stage progression modal with execution stats.

---

## 6. Reviewing and approving recommendations

Each recommendation card is a governed item with a lifecycle: `PROPOSED → REVIEWED → APPROVED` (or `REJECTED`), then optionally `ACTIONED → MEASURED`. Items expire after 7 days.

- **Approve (policy-checked)** reviews and approves in one click using a demo identity (`pricing_manager`). The server runs the policy checks: known cost of goods, margin floor (default 10% of price), price floor/ceiling, MAP when known, maximum change (default 30%), currency, region and stock. If any check fails, the card shows the violations and nothing changes.
- A successful approval is **a decision record only**. The dashboard then shows a dry run of what would be applied. No price is changed anywhere, because downstream writes are disabled and no repricer or ERP integration ships.
- The demo identity is **not authentication**. Do not expose this application to untrusted networks.
- Every step is recorded in a hash-chained audit trail: `GET /api/v1/audit`, verify with `GET /api/v1/audit/verify`.
- The demo catalogue has no sales volume or elasticity data, so recommendations carry an explicit "missing inputs" note instead of a margin-impact range. Dollar figures shown on cards come from the demo engine and use assumed volumes; treat them as illustrative.

### Using the API directly

```bash
# list recommendations (registers them as governed items; note each workflow_id)
curl localhost:8000/api/v1/recommendations | jq '.top_actions[0].workflow_id'

# review as an analyst, approve as a manager
curl -X POST localhost:8000/api/v1/recommendations/$ID/review  -H 'X-Actor-Id: ana' -H 'X-Actor-Role: analyst'         -H 'Content-Type: application/json' -d '{}'
curl -X POST localhost:8000/api/v1/recommendations/$ID/approve -H 'X-Actor-Id: pat' -H 'X-Actor-Role: pricing_manager' -H 'Content-Type: application/json' -d '{}'

# dry run (the default); dry_run=false is refused while writes are disabled
curl -X POST localhost:8000/api/v1/recommendations/$ID/execute -H 'X-Actor-Id: pat' -H 'Content-Type: application/json' -d '{"idempotency_key":"run-0001"}'
```

### Importing listings

Register a source with a documented permission basis, then upload a CSV or JSON file:

```bash
curl -X PUT localhost:8000/api/v1/sources/acme-feed -H 'Content-Type: application/json' -d '{
  "source_id":"acme-feed","competitor_id":"acme","merchant":"Acme","country":"US","currency":"USD",
  "source_type":"PARTNER_FEED","policy":{"permitted":true,"basis":"Partner feed agreement 2026-01"}}'
curl -X POST 'localhost:8000/api/v1/imports?source_id=acme-feed&fmt=csv' --data-binary @listings.csv
curl 'localhost:8000/api/v1/observations/history?kind=price&listing_id=ACME-1&as_of=2026-11-01T00:00:00Z'
```

Rows that are malformed are reported and rejected, not repaired. Rows with instruction-like text are stored but quarantined and excluded from history unless `include_quarantined=true`.
