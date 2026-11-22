# Software Architecture Decision Record (SADR)

**Product:** AURORA, retail competitor intelligence
**Purpose:** Records the significant architectural decisions, the reasons, and what each costs. It supersedes the former `ARCHITECTURE.md`, whose claims about tiers, cloud services and benchmark results were inconsistent with the code.
**Format:** each record has Context, Decision, Consequences and Status. Status values: *Accepted* (in the code), *Accepted, partial* (decision made, implementation incomplete), *Proposed* (not built).

Diagrams: [system context](../diagrams/rendered/01-system-context.svg) · [components](../diagrams/rendered/02-architecture-components.svg) · [trust boundaries](../diagrams/rendered/11-security-trust-boundaries.svg) · [all](../diagrams/README.md).

## Index

| ID | Decision | Status |
|---|---|---|
| ADR-001 | Deterministic code first; ML ranks; LLMs are bounded and advisory | Accepted |
| ADR-002 | Four tiers with one naming scheme | Accepted |
| ADR-003 | Preserve the existing app; add a governed domain layer beside it | Accepted |
| ADR-004 | SQLite as the system of record for the governed layer, behind small protocols | Accepted, partial |
| ADR-005 | Immutable, provenance-carrying observations with "as of" queries | Accepted |
| ADR-006 | Hash-chained audit log | Accepted |
| ADR-007 | Recommendations only; write integrations disabled by default | Accepted |
| ADR-008 | Recommendation lifecycle with server-side policy gates | Accepted |
| ADR-009 | Source compliance gate; permission is never assumed | Accepted |
| ADR-010 | Report only measured metrics; unmeasured means omitted | Accepted |
| ADR-011 | Decimal money and explicit units, tax, shipping and conditions | Accepted |
| ADR-012 | Availability: unknown is not out-of-stock; phantom inventory is a hypothesis | Accepted |
| ADR-013 | Demo identity headers instead of real auth, until B-01 | Accepted (temporary) |
| ADR-014 | One cloud target first; scaffolds are not claims | Accepted, partial |
| ADR-015 | Untrusted content handling | Accepted, partial |
| ADR-016 | Route the live pipeline through the new match classes | Proposed |

---

## ADR-001: Deterministic code first; ML ranks; LLMs are bounded and advisory

**Context.** Pricing decisions depend on exact arithmetic and hard rules. LLMs are non-deterministic and can be steered by page content.
**Decision.** Rules, calculations, validation and policy enforcement are plain code. ML handles retrieval, ranking and anomaly detection. LLM agents investigate ambiguous matches and explain; their output is a suggestion that cannot approve or execute anything.
**Consequences.** Most volume never reaches an LLM (cheaper, reproducible). Agent output must be validated against typed schemas. The simulated LLM means this boundary is designed but not yet stress-tested against a real model.
**Status.** Accepted.

## ADR-002: Four tiers with one naming scheme

**Context.** Earlier documents called the design "tri-tier" while describing four stages, and listed different thresholds in different places.
**Decision.** Four tiers everywhere: (1) deterministic rules, (2) classical ML, (3) agentic arbitration, (4) human review. Tier 2 splits at τ ≥ 0.92 (auto-commit), 0.65–0.92 (agents), < 0.40 (no equivalent); those values live in settings.
**Consequences.** Docs, UI and code agree. The thresholds are universal defaults, not calibrated per category (plan section 2.3 requires calibration; B-10).
**Status.** Accepted.

## ADR-003: Preserve the existing app; add a governed domain layer beside it

**Context.** The plan says to reuse working components, not replace them for novelty.
**Decision.** Keep the FastAPI app, routes, agents, ML modules and UI. Add `retail_intel.domain`, a dependency-light layer implementing the plan's data model, pricing, availability, signals, sources, safety, audit and recommendation lifecycle. Wire it into the API where it replaces something fake (recommendation approval, audit, import, history) and leave the rest as libraries.
**Consequences.** Low regression risk, and the domain layer is testable without FastAPI or models. The cost is two coexisting vocabularies (legacy verdicts vs `MatchClass`; legacy effective price vs `compute_effective_price`) until ADR-016/B-16 close the gap.
**Status.** Accepted.

## ADR-004: SQLite as the system of record for the governed layer, behind small protocols

**Context.** The plan wants separate raw-evidence, operational, analytical, vector and graph stores, and cloud providers behind interfaces, without making the graph or vector index the only record.
**Decision.** Use stdlib SQLite (file or in-memory) for evidence, observations, recommendations and audit. The audit log depends on an `AuditSink` protocol; the workflow depends on the store through a narrow interface. The graph (NetworkX) and vector index (in-process) are derived and rebuildable.
**Alternatives.** Postgres from day one (heavier local setup, no new guarantee at demo scale); BigQuery (needs cloud, not locally reproducible).
**Consequences.** Zero-install local dev and trivial test isolation; SQLite triggers give cheap append-only enforcement. Not suitable for multi-worker or multi-node writes, no object storage for large evidence, no warehouse. Moving to Postgres/GCS/BigQuery means implementing the same protocols. Source registry, users and schedules are not yet persisted (B-02).
**Status.** Accepted, partial.

## ADR-005: Immutable, provenance-carrying observations with "as of" queries

**Context.** Competitive history is evidence. Overwriting current values destroys the ability to reproduce a past decision.
**Decision.** Every price, availability and promotion datum is an append-only `Observation` with provenance (method, source, retrieval time, parser version, payload hash, evidence reference, run id). IDs are deterministic from content, so re-ingestion is idempotent. Queries accept `as_of`, filtering on retrieval time, so late or corrected data cannot rewrite what was known at T. Raw payloads are stored content-addressed in an `evidence` table. Quarantined rows stay stored but are excluded by default.
**Consequences.** Reproducible history and cheap de-duplication. Storage grows monotonically; a retention/deletion policy is needed (not built). Corrections are new observations, not edits.
**Status.** Accepted.

## ADR-006: Hash-chained audit log

**Context.** Decisions and denials must be reviewable and tamper-evident.
**Decision.** Each audit event includes the previous event's hash; `verify()` recomputes the chain. The table is append-only by trigger.
**Consequences.** Detects edits, removals and reordering at near-zero cost. Does not prevent a privileged actor from rewriting the whole chain; anchoring hashes externally is a future option. Concurrent writers are serialised by a lock within one process only.
**Status.** Accepted.

## ADR-007: Recommendations only; write integrations disabled by default

**Context.** A match is not a price recommendation, and a recommendation is not an approved change. Autonomous repricing is out of scope for the initial release.
**Decision.** The system produces and tracks recommendations. `execute` is dry-run by default and idempotent per key. A real write requires three things at once: `WRITES_ENABLED=true`, a configured `WriteIntegration`, and an `APPROVED` recommendation. No integration ships with the repository.
**Consequences.** Safe by default; the "Push to Repricer" button became "Approve (policy-checked)" and the former `/approve` endpoint that pretended to dispatch to a repricer/ERP was removed (breaking change). Adding a repricer integration is deliberate work with its own limits, rollback and review.
**Status.** Accepted.

## ADR-008: Recommendation lifecycle with server-side policy gates

**Decision.** States `PROPOSED → REVIEWED → APPROVED | REJECTED → ACTIONED → MEASURED`, plus `EXPIRED`. Review needs analyst or above; approval needs pricing manager, category manager or admin and passes `PolicyEngine` (currency, region, stock for promotions, known COGS, margin floor, price floor/ceiling, MAP, maximum change). The policy context is built on the server from the catalogue, never from the client. A blocked approval is audited and leaves the item in `REVIEWED`. Unknown cost blocks approval rather than being assumed.
**Consequences.** A recommendation cannot skip review or violate configured limits through the API. The demo catalogue lacks MAP and elasticity, so those checks and financial ranges are inactive or reported as gaps until real inputs exist.
**Status.** Accepted.

## ADR-009: Source compliance gate; permission is never assumed

**Decision.** A source defaults to "not permitted". Use requires a recorded `basis`, no revocation, and an allowed action. A fixed set of actions (bypass authentication/paywall, solve CAPTCHA, evade rate limits, place order, checkout, create account, pay) is refused for every source. The gate runs before any raw data is stored. Source types are ranked official API > partner feed > licensed provider > public page > manual upload > demo.
**Consequences.** Compliance is enforced in code, not only policy text. Because no live adapter exists, the gate currently protects the import path only. A person still has to do the legal review that fills `basis`.
**Status.** Accepted.

## ADR-010: Report only measured metrics; unmeasured means omitted

**Context.** The repository previously displayed constants (latency, recall, faithfulness, "margin protected") as live telemetry, and reported 100% golden accuracy by scoring scripted answers.
**Decision.** The metrics engine returns only values derived from recorded analyses or live drift calculations; anything else is omitted (`None`, excluded from JSON). The registry ships no fabricated metrics. Golden evaluation runs each benchmark SKU through the real pipeline and lists misses; an empty benchmark scores 0, not 1. Dollar figures built on assumed volumes are named, labelled illustrative, and the recommendation layer states an explicit gap instead.
**Consequences.** Numbers on screen may be fewer, and the honest benchmark result is 7/8, not 100%. The UI shows nothing or `n/a` where nothing was measured. Offline model-quality metrics need an evaluation job (B-10).
**Status.** Accepted.

## ADR-011: Decimal money and explicit units, tax, shipping and conditions

**Decision.** All prices use `Decimal`. Effective price is a function returning an itemised breakdown and the assumptions used. Shopper conditions (membership, new customer, app-only, payment instrument, geography, personalised) are never assumed; basket conditions are computed from the basket; code/clip steps are applied and shown. Cross-currency needs supplied FX rates. Unit normalisation refuses to mix dimensions.
**Consequences.** Comparisons are like-for-like and explainable; callers must state tax/shipping treatment. Extracting offers from page text is separate and not built.
**Status.** Accepted.

## ADR-012: Availability: unknown is not out-of-stock; phantom inventory is a hypothesis

**Decision.** `UNKNOWN` is a first-class state. Phantom-inventory claims require repeated corroborating samples and are emitted as a hypothesis with caveats. No code infers competitor stock quantities.
**Consequences.** Fewer confident "phantom" calls. The legacy Tier-3 path still derives `UNFULFILLED_PHANTOM` from a single listing; replacing it is part of B-09/B-16.
**Status.** Accepted.

## ADR-013: Demo identity headers instead of real authentication, until B-01

**Context.** Real RBAC/SSO is substantial and out of this iteration's scope, but the approval workflow needs an actor and role for its audit trail and role checks.
**Decision.** Read `X-Actor-Id` and `X-Actor-Role` from the request. Default is `anonymous`/`viewer`, which cannot review or approve. Document loudly that this is **not authentication**.
**Consequences.** Anyone who can reach the API can claim any role. Acceptable only on localhost or a trusted network. Terraform therefore defaults `allow_public_access=false`. Replace `_actor()` with a real dependency (B-01).
**Status.** Accepted (temporary).

## ADR-014: One cloud target first; scaffolds are not claims

**Decision.** GCP is the first cloud target and AWS a later adapter, per the plan. The repository contains terraform for both (Cloud Run + Artifact Registry; App Runner + ECR). Documentation must say they are unvalidated and must not list services that are not provisioned.
**Consequences.** Earlier text described Pub/Sub, BigQuery, Spanner and Vertex AI as deployed; they appear only as settings. The Cloud Run public invoker binding is now opt-in.
**Status.** Accepted, partial. Validation, load tests and a restore drill remain (B-17).

## ADR-015: Untrusted content handling

**Decision.** Treat all source text as hostile. `scan_untrusted_text` flags instruction overrides, role hijacks, exfiltration requests, chat markup, tool-call syntax, hidden HTML and zero-width characters; suspicious rows are quarantined on import (stored, excluded). `wrap_for_llm` and `clean_text` exist to present text to a model as data with truncation.
**Consequences.** Heuristic, not a guarantee. The scanner currently runs on the importer path only; the agents do not yet call it. Tool allow-listing and argument validation are also outstanding (B-18).
**Status.** Accepted, partial.

## ADR-016: Route the live pipeline through the new match classes

**Context.** The live `/intelligence/analyze` still returns legacy verdict strings, so the hard-conflict guard, the eight classes and persisted decision records are not on the main path.
**Proposal.** Map Tier-1/2/3 outputs onto `MatchClass`, always pass proposals through `guard_auto_match`, persist a `MatchDecision` with evidence and model version, and keep a compatibility field with the legacy verdict for the UI during migration.
**Consequences if adopted.** The golden benchmark expectations change (e.g. `EQUIVALENT_PRIVATE_LABEL` → `PRIVATE_LABEL_EQUIVALENT`) and need a labelled set large enough to calibrate thresholds.
**Status.** Proposed (B-09, B-10).

---

## Appendix: quality attributes

| Attribute | Approach | Evidence level |
|---|---|---|
| Correctness of money | Decimal, tested edge cases | Unit tests |
| Auditability | Provenance + hash chain + decision records | Unit and handler tests |
| Safety | Dry-run default, policy gates, disabled writes | Unit and handler tests |
| Compliance | Gate before storage; never-permitted set | Unit tests |
| Honesty of reporting | ADR-010 | Unit tests; live eval |
| Scalability | Single process today; queues/workers planned | None; no load test claim |
| Security | Demo identity only; see TSD section 9 | Gaps documented |
