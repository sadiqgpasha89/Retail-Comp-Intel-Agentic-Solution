# Enterprise Architectural Document Record (ADR): Retail Competitor Intelligence Autonomous Hybrid Solution

---

## 1. System Context & Overview

The **AURORA Retail Competitor Intelligence Platform** is designed to eliminate margin erosion, detect competitor promotional evasion, and autonomously arbitrate SKU equivalence at enterprise scale (20,000+ data points, 48 retail competitors, 10 categories).

```mermaid
graph TB
    subgraph "Edge Perimeter (48 Competitors)"
        C1[Amazon / Walmart / Target]
        C2[Wayfair / Best Buy / Sephora]
        C3[Digital DTC Marketplaces]
    end

    subgraph "Stage 1 & 2: Ingestion & Normalization"
        Ingest[Headless Scraper Mesh & DOM Harvester]
        Norm[Normalization Pipeline]
        Honeypot[Honeypot & Phantom Interceptor]
    end

    subgraph "Stage 3: Tri-Tier Hybrid Resolution"
        T1[Tier 1: Deterministic Rule Engine]
        T2[Tier 2: Classical ML Bi/Cross-Encoder]
        T3[Tier 3: Multi-Agent Cognitive Mesh]
        HITL[Tier 4: Merchandiser HITL Queue]
    end

    subgraph "Stage 4 & 5: Causal Intelligence & Knowledge Graph"
        KG[(3D Retail Knowledge Graph)]
        Anom[Isolation Forest Anomaly Detector]
        Causal[Causal Strategy & Elasticity Engine]
    end

    subgraph "Stage 6: Action Orchestration"
        Reprice[Dynamic Repricer Feeds]
        Legal[MAP Compliance Notices]
        Recs[Executive Merchandising Directives]
        ERP[ERP Procurement Triggers]
    end

    C1 & C2 & C3 --> Ingest
    Ingest --> Honeypot --> Norm
    Norm --> T1
    T1 -- "No GTIN (τ < 1.0)" --> T2
    T2 -- "0.65 ≤ τ < 0.92" --> T3
    T2 -- "τ ≥ 0.92 (Auto-Commit)" --> Causal
    T1 -- "GTIN Match (τ = 1.0)" --> Causal
    T3 -- "Contradiction / τ < 0.65" --> HITL
    T3 -- "Resolved" --> Causal
    Causal <--> KG
    Norm --> Anom --> Causal
    Causal --> Recs & Reprice & Legal & ERP
```

---

## 2. Tri-Tier Hybrid Decision Boundary Architecture

To balance **throughput (>150 SKUs/s)**, **sub-cent execution cost**, and **cognitive precision**, the resolution fabric implements a calibrated 3-tier hybrid routing topology:

```mermaid
flowchart TD
    Input([Incoming Scraped Competitor SKU]) --> Step1{GTIN / Barcode Parity?}
    
    %% Tier 1
    Step1 -- "Yes (Deterministic Match)" --> T1Commit[Tier 1: Immediate GTIN Auto-Commit<br/>Latency: < 0.5ms | Cost: $0.0000]
    Step1 -- "No Barcode / Obscured" --> Step2[Bi-Encoder Dense Retrieval<br/>HNSW Vector Search Top-K Candidates]
    
    %% Tier 2
    Step2 --> Step3[Cross-Encoder Fine-Grained Scoring<br/>Feature Compatibility Score τ]
    Step3 --> SplitDecision{Evaluate Score τ}
    
    SplitDecision -- "τ ≥ 0.92 (High Confidence)" --> T2Commit[Tier 2: Auto-Commit Direct Substitute<br/>Latency: 8.5ms | Cost: $0.0001]
    SplitDecision -- "0.65 ≤ τ < 0.92 (Ambiguous)" --> T3Escalate[Tier 3: Escalate to Multi-Agent Mesh<br/>Latency: 120ms | Cost: $0.0024]
    SplitDecision -- "τ < 0.40 (Definitive Mismatch)" --> Reject[Auto-Reject Mismatch]
    
    %% Tier 3
    T3Escalate --> Supervisor[Supervisor Agent: P-E-R-R Reasoning Loop]
    Supervisor --> T3Decision{Arbitration Verdict}
    T3Decision -- "Evidence Harmonized" --> T3Commit[Tier 3: Commit Cognitive Match]
    T3Decision -- "Multimodal Clash / Irresolvable" --> HITLQueue[Tier 4: Human Merchandiser HITL Queue]
    
    T1Commit & T2Commit & T3Commit --> Output([Downstream Causal Strategy Engine])
```

---

## 3. Multi-Agent Cognitive Mesh: Plan-Execute-Reflect-Report (P-E-R-R)

When ambiguity or promotional evasion is detected, the **Supervisor Agent** orchestrates sandboxed specialized sub-agents:

```mermaid
sequenceDiagram
    autonumber
    actor System as Pipeline Coordinator
    participant Sup as Supervisor Agent
    participant Promo as Shopper Promo Agent
    participant Matcher as Equivalence Matcher Agent
    participant KG as Retail Knowledge Graph
    participant Guard as Reflection Guard (Hierarchy of Truth)
    participant Strat as Strategy Agent

    System->>Sup: Resolve Ambiguous SKU (τ = 0.78)
    Note over Sup: PHASE 1: PLAN<br/>Decompose into verification sub-tasks
    
    Sup->>Promo: Clip coupons & simulate checkout basket
    Promo-->>Sup: Discovered $150 hidden cart drop & voucher
    
    Sup->>Matcher: Verify physical equivalence & OEM links
    Matcher->>KG: Query OEM factory & patent relationships
    KG-->>Matcher: Shared Dongguan Fab & Patent PAT-2024-8871
    Matcher-->>Sup: Candidate is EQUIVALENT_PRIVATE_LABEL
    
    Note over Sup: PHASE 3: REFLECT<br/>Audit evidence against Hierarchy of Truth
    Sup->>Guard: Validate Title claim vs OCR specs & OEM patent
    Guard-->>Sup: Hierarchy Consistent (Tier 2 Specs Override Tier 4 Text)
    
    Note over Sup: PHASE 4: REPORT<br/>Synthesize causal strategy & margin impact
    Sup->>Strat: Calculate cross-price elasticity & counter-action
    Strat-->>Sup: Directive: OEM Private-Label Arbitrage (+48% GM)
    Sup-->>System: Final Intelligence Payload (Confidence: 96.0%)
```

---

## 4. End-to-End 6-Stage Operational Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Stage1_PerimeterDiscovery
    Stage1_PerimeterDiscovery --> Stage2_MultimodalIngestion: Discovered Sitemaps & PDPs
    Stage2_MultimodalIngestion --> Stage3_EntityResolution: Normalized JSON Payload
    Stage3_EntityResolution --> Stage4_SignalAnomalyDetection: Harmonized GPC & SKU Match
    Stage4_SignalAnomalyDetection --> Stage5_CausalSynthesis: Anomaly & Price Shift Signals
    Stage5_CausalSynthesis --> Stage6_ActionOrchestration: Causal Intent Hypothesis
    Stage6_ActionOrchestration --> [*]: Dispatched to Repricer & ERP
    
    state Stage1_PerimeterDiscovery {
        [*] --> DomainMapping
        DomainMapping --> TaxonomyCrawling
        TaxonomyCrawling --> [*]
    }
    
    state Stage2_MultimodalIngestion {
        [*] --> DOMHarvesting
        DOMHarvesting --> VisionOCRInspection
        VisionOCRInspection --> HoneypotQuarantine
        HoneypotQuarantine --> [*]
    }
    
    state Stage3_EntityResolution {
        [*] --> Tier1Rules
        Tier1Rules --> Tier2ClassicalML
        Tier2ClassicalML --> Tier3MultiAgent
        Tier3MultiAgent --> [*]
    }
    
    state Stage5_CausalSynthesis {
        [*] --> KnowledgeGraphTraversal
        KnowledgeGraphTraversal --> ElasticitySimulation
        ElasticitySimulation --> [*]
    }
```

---

## 5. 4-Tier Hierarchy of Truth Guardrail Engine

To prevent catastrophic hallucinations and deceptive packaging errors, the multi-agent mesh strictly enforces the **4-Tier Hierarchy of Truth**:

```mermaid
graph TD
    T1["👑 Tier 1: Customer Review Imagery & Verified Photos<br/>(Physical Ground Truth: Packaging, labels, real-world chassis)"]
    T2["🥈 Tier 2: Manufacturer Spec Tables & GTIN-14 Barcodes<br/>(Contractual Ground Truth: Wattage, dimensions, unit counts)"]
    T3["🥉 Tier 3: High-Res PDP Hero Imagery & Viewport Renders<br/>(Visual Representation: Hero photos, front panel angles)"]
    T4["📜 Tier 4: Textual Marketing Titles, Descriptions, Taglines<br/>(Adversarial / Error-Prone: '3-Pack Bundle', '2026 Edition')"]

    T1 -->|Overrides| T2
    T2 -->|Overrides| T3
    T3 -->|Overrides| T4

    classDef t1 fill:#10b981,stroke:#fff,stroke-width:2px,color:#000;
    classDef t2 fill:#06b6d4,stroke:#fff,stroke-width:2px,color:#000;
    classDef t3 fill:#a855f7,stroke:#fff,stroke-width:2px,color:#fff;
    classDef t4 fill:#f59e0b,stroke:#fff,stroke-width:2px,color:#000;

    class T1 t1;
    class T2 t2;
    class T3 t3;
    class T4 t4;
```

---

## 6. Cloud-Native Dual-Stack Architecture (GCP vs AWS)

```mermaid
graph LR
    subgraph "Google Cloud Platform (GCP Production Stack)"
        GCP_Ingest[Cloud Run Jobs + Cloud Scheduler]
        GCP_Stream[Cloud Storage + Pub/Sub]
        GCP_ML[GKE Autopilot + Vertex AI Vector Search]
        GCP_Graph[Spanner Graph]
        GCP_Agent[Vertex AI Gemini 1.5 Pro / Flash]
        GCP_OLAP[BigQuery Analytics]
        
        GCP_Ingest --> GCP_Stream --> GCP_ML --> GCP_Graph --> GCP_Agent --> GCP_OLAP
    end

    subgraph "Amazon Web Services (AWS Production Stack)"
        AWS_Ingest[ECS Fargate Tasks + EventBridge]
        AWS_Stream[S3 Data Lake + Amazon MSK Kafka]
        AWS_ML[AWS EKS GPU + OpenSearch Vector]
        AWS_Graph[Amazon Neptune]
        AWS_Agent[Amazon Bedrock Claude 3.5 Sonnet]
        AWS_OLAP[Amazon Redshift Serverless]
        
        AWS_Ingest --> AWS_Stream --> AWS_ML --> AWS_Graph --> AWS_Agent --> AWS_OLAP
    end
```

---

## 7. Statistical Drift Radar Mathematical Model

The continuous telemetry fabric evaluates three mathematical drift dimensions across live ingestion batches:

1. **Population Stability Index (PSI)** for Ingestion Covariate Shift:
   $$\text{PSI} = \sum_{b=1}^{B} \left( P_b - Q_b \right) \times \ln\left(\frac{P_b}{Q_b}\right)$$
   - $\text{PSI} < 0.10$: Stable baseline
   - $0.10 \le \text{PSI} < 0.25$: Covariate warning (Drift alert logged)
   - $\text{PSI} \ge 0.25$: Critical covariate drift (Triggers automatic re-normalization)

2. **Wasserstein Distance (Earth Mover's Distance)** for Embedding Cluster Shift:
   $$W_1(u, v) = \int_{-\infty}^{\infty} |U(x) - V(x)| dx$$
   - Monitors spatial drift between baseline product vectors and newly ingested embeddings.

3. **Page-Hinkley Sequential Test** for Concept Decay:
   $$m_t = \sum_{i=1}^{t} (e_i - \bar{e} - \delta), \quad M_t = \min_{1 \le i \le t} m_i, \quad PH_t = m_t - M_t$$
   - Triggers model retraining when $PH_t > \lambda$ threshold (Default: $\lambda = 50.0$).
