# Business Requirements Document (BRD)

**Product:** AURORA, retail competitor intelligence
**Status:** Draft v1.0, derived from the implementation plan. Delivery status is tracked in [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md); where this document says *shall*, the matrix says whether it is built.

---

## 1. Purpose and background

Retailers monitor competitors by hand or with price-comparison tools that stop at "their price is lower". That answer is often wrong or unactionable: the competitor SKU may be a different pack size, the price may require a membership or a basket threshold, the item may be unobtainable, or the page may be adversarial content.

AURORA is meant to deliver **decision-ready, evidence-backed competitive intelligence**: what competitors offer, which of their products truly correspond to ours, what the comparable price really is, what changed, how reliable the signal is, and what action the business could consider. It recommends; humans decide.

This repository is currently a **demonstrable reference implementation on synthetic data**. It is not connected to live competitor sources and is not production-ready.

## 2. Business objectives

| # | Objective | How success is judged |
|---|---|---|
| O1 | Reduce time pricing and category teams spend finding and verifying competitor moves | Time from competitor change to reviewed recommendation (to be measured once real sources exist) |
| O2 | Avoid harmful pricing decisions caused by false product equivalence | False-positive match rate tracked separately from accuracy |
| O3 | Compare prices like-for-like, including promotions, shipping and conditions | Effective-price breakdown available for every comparison |
| O4 | Keep every recommendation explainable and auditable | Each recommendation has evidence, assumptions, owner, decision history |
| O5 | Keep the business in control of changes | No price change leaves the system without explicit approval and a configured integration |
| O6 | Stay within legal and contractual limits when collecting data | Zero collection from sources without a recorded permission basis |

No business-impact figure (revenue protected, margin gained, hours saved) is claimed by this document. Any such number must come from measured pilot data.

## 3. Stakeholders and users

| Persona | Needs |
|---|---|
| Category / merchandising manager | Assortment gaps, product matches, competitor changes |
| Pricing manager | Promotion-adjusted comparable prices, margin risk, recommendations to review and approve |
| Brand / compliance team | Advertised-price monitoring, evidence packs, flagged policy exceptions (for human review only) |
| Executive | Market position, key movements, exposure, priorities |
| Analyst / administrator | Source configuration, data quality, matching review, agent traces, system health |

## 4. Scope

### In scope
1. Competitor and source registry with recorded permission and policy per source
2. Ingestion of competitor listings from permitted feeds and manual CSV/JSON upload, with full provenance
3. Product identity resolution with explicit match classes and human review
4. Price, promotion and availability intelligence with transparent effective-price calculation
5. Market signals, anomaly detection and labelled hypotheses
6. Recommendations with a review/approve/reject/action/measure lifecycle and policy gates
7. Dashboards for the personas above
8. Audit trail, security, and quality/drift evaluation

### Out of scope (initial release)
- Access to competitor accounts, private APIs, paywalled or restricted pages
- CAPTCHA or access-control evasion, stealth scraping, bypassing rate limits
- Purchases, checkout, payments, account creation, fake customer activity
- Autonomous repricing, promotion publication, procurement or legal notices
- Claims of exact competitor inventory, competitor intent, causal effects or market share the evidence cannot support
- Customer-level profiling or sensitive-attribute inference
- A general-purpose web-search agent
- Simultaneous production support for every cloud provider

## 5. Business requirements

Each requirement has an ID used in the FSD for traceability.

### Data acquisition and compliance
- **BR-01** The business shall maintain a registry of competitors and sources, with region, currency, channel, categories, priority and collection schedule.
- **BR-02** Data shall be collected only from sources whose permission basis is recorded (official API, partner feed, licensed provider, permitted public page, or manual upload). Where permission is unclear or revoked, the source shall be blocked.
- **BR-03** The system shall never bypass authentication, paywalls, CAPTCHAs, rate limits or other technical restrictions, and shall never place orders.
- **BR-04** Every observation shall carry provenance: method, source, retrieval time, parser version, payload hash and evidence reference.
- **BR-05** Users shall be able to upload CSV/JSON listings and use bundled demo data.

### Product understanding
- **BR-06** The system shall detect new, removed and changed competitor listings and assortment gaps.
- **BR-07** The system shall resolve equivalence using deterministic rules first, ML second, bounded agent investigation third, and human review for the rest.
- **BR-08** Matches shall use explicit classes (exact, equivalent variant, direct substitute, private-label equivalent, complementary, related, no match, needs review) and record evidence, method, confidence, version and reviewer overrides.
- **BR-09** The system shall not silently auto-match products that differ materially in pack size, model, capacity, generation or bundle.

### Price, promotion, availability
- **BR-10** The system shall compute an effective comparable price with a visible breakdown and explicit tax/shipping treatment, normalised for unit and currency.
- **BR-11** Conditional offers (membership, new customer, app-only, payment instrument, quantity threshold, geography) shall be distinguished from generally available prices.
- **BR-12** Price, promotion and availability history shall be retained and reproducible "as of" a chosen time.
- **BR-13** Unknown availability shall never be reported as out of stock; phantom inventory shall be treated as a hypothesis requiring corroboration.
- **BR-14** Possible MAP or contractual issues shall be flagged for human review, never asserted automatically.

### Insight and decision
- **BR-15** The system shall detect and rank price moves, promotions, assortment and availability changes, and show the evidence behind each.
- **BR-16** Explanations of competitor behaviour shall be labelled as hypotheses with alternatives and confidence.
- **BR-17** Financial impact shall be estimated only when internal sales, cost and elasticity inputs exist; otherwise the system shall state what is missing. Estimates shall show assumptions and ranges.
- **BR-18** Recommendations shall follow a lifecycle (proposed, reviewed, approved/rejected, actioned, measured) with owner, rationale, assumptions, expiry and outcome.
- **BR-19** Approval shall be blocked when margin floor, MAP, price bounds, currency, region or stock rules are violated.
- **BR-20** The system shall default to recommendations only. Any downstream write requires an explicit integration, configured limits, dry-run and human approval.
- **BR-21** Users shall be able to ask questions in natural language and receive answers grounded in cited observations.
- **BR-22** The business shall be able to configure alerts, scheduled reports and exports.

### Trust and operations
- **BR-23** Access shall be role-based with tenant isolation; credentials shall be held in a secrets manager.
- **BR-24** Web content and retrieved documents shall be treated as untrusted; prompt injection shall not be able to change system behaviour or bypass policy.
- **BR-25** Match quality, promotion extraction, availability classification, anomaly precision and LLM groundedness shall be evaluated against a labelled benchmark, with false positives tracked separately.
- **BR-26** Source freshness, parser errors, drift and cost per monitored SKU shall be monitored.
- **BR-27** The system shall not describe itself as production-ready until real adapters, load tests, security review and deployment validation have passed.

## 6. Assumptions and constraints

- Internal cost, sales, inventory and elasticity data are required for financial estimates and are not available in the demo; the system reports an explicit gap instead of inventing a number.
- A single validated cloud target (GCP first) is preferred over several partial ones.
- Legal review of each source's terms and robots directives is a business responsibility; the system records the outcome, it does not decide it.
- The demo catalogue is synthetic and carries no currency, MAP or elasticity data. Currency is assumed USD and labelled so.

## 7. Risks

| Risk | Impact | Mitigation in design | Residual |
|---|---|---|---|
| False equivalence leads to a wrong price decision | High | Hard-conflict guard, review routing, false-positive tracking, human approval | Matching is currently heuristic; benchmark is 8 cases |
| Unauthorised or disallowed collection | High | Compliance gate, permission register, never-permitted actions | No live adapter yet to enforce against |
| Prompt injection from competitor content | High | Scan/quarantine on import, LLM output is advisory | Agents do not yet wrap or scan source text; LLM path is simulated and untested live |
| Fabricated or inflated metrics erode trust | High | Metrics report only measured values; capability matrix; eval is live | Demo impact figures remain illustrative |
| No real authentication | High | Role header is documented as demo identity; terraform public access defaults off | Must be solved before any shared deployment |
| Over-reliance on automation | Medium | Recommendations only; approval and policy gates; dry-run | |

## 8. Success measures (to be baselined with real data)

- Match precision, recall, F1 by category and class; false-positive rate
- Share of recommendations reviewed within SLA; acceptance rate; measured outcome vs estimate
- Source freshness and success rate; parser error rate
- Alert usefulness (acted-on vs dismissed)
- Cost per monitored SKU

No target values are set here because none can be justified without real data and a pilot.

## 9. Acceptance

The plan defines twelve end-to-end scenarios. Their current status is recorded in [FSD.md section 9](FSD.md#9-acceptance-scenario-status).

## 10. Traceability

BR IDs map to functional requirements in the [FSD](FSD.md), to design decisions in the [SADR](SADR.md), and to implementation status in the [capability matrix](CAPABILITY_MATRIX.md).
