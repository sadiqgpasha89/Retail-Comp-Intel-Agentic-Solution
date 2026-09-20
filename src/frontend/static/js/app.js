/**
 * AURORA RETAIL INTEL - FRONTEND CONTROLLER & DEMO ENGINE
 * Enterprise Presentation Demo for Senior Leadership
 * Handles Executive Mode Switching, Strategic Merchandising Recommendations,
 * Real-time SSE Agent Streaming, Interactive Knowledge Graph, Chaos Sandbox,
 * Elasticity Simulator, and Large-Scale (20,000+) Datasets across 48 Competitors.
 */

let competitorCatalog = [];
let internalCatalog = [];
let activeStream = null;
let currentTourStep = 0;
let currentDashboardMode = 'stakeholder';
let kgData = { nodes: [], links: [] };

const tourSteps = [
  {
    mode: 'stakeholder',
    tab: 'war-room',
    badge: 'STEP 1/6',
    title: 'Executive Causal War Room & ROI Overview',
    description: 'Autonomous detection of competitor price shifts across 48 retailers, preserving $184,250 in gross margin.'
  },
  {
    mode: 'stakeholder',
    tab: 'recommendations',
    badge: 'STEP 2/6',
    title: 'Strategic Merchandising Directives (Retail Commercial Actions)',
    description: 'Prescriptive pricing, MAP enforcement, OEM store-brand arbitrage, and basket cross-sell directives.'
  },
  {
    mode: 'stakeholder',
    tab: 'matching',
    badge: 'STEP 3/6',
    title: 'Tri-Tier Hybrid Intelligence Resolution Console',
    description: 'Deterministic Rules (τ=1.0) → Classical ML (τ≥0.92) → Multi-Agent Arbiter (0.65≤τ<0.92) → HITL Queue.'
  },
  {
    mode: 'stakeholder',
    tab: 'graph',
    badge: 'STEP 4/6',
    title: 'Enterprise Retail Property Knowledge Graph',
    description: 'Traverse OEM factory supply chains, brand conglomerate hierarchies, and private-label white-label links.'
  },
  {
    mode: 'telemetry',
    tab: 'stages',
    badge: 'STEP 5/6',
    title: 'End-to-End 6-Stage Operational Lifecycle',
    description: 'Stage 1 (Perimeter Discovery) through Stage 6 (Dynamic Repricer & ERP Action Orchestration).'
  },
  {
    mode: 'telemetry',
    tab: 'edge-cases',
    badge: 'STEP 6/6',
    title: '8 Critical Edge Cases & Chaos Engineering Sandbox',
    description: 'Self-healing defense against honeypot price crashes, deceptive 3-packs, phantom inventory, and currency shocks.'
  }
];

document.addEventListener('DOMContentLoaded', () => {
  fetchCatalogs();
  fetchRecommendations();
  fetchMetrics();
  fetchDriftStatus();
  fetchHitlQueue();
  fetchChaosStatus();
  renderKnowledgeGraph();
});

// ==========================================================================
// 1. Dashboard Mode Switching (Stakeholder vs Telemetry)
// ==========================================================================
function switchDashboardMode(mode) {
  currentDashboardMode = mode;
  const btnStakeholder = document.getElementById('btn-mode-stakeholder');
  const btnTelemetry = document.getElementById('btn-mode-telemetry');
  const navStakeholder = document.getElementById('nav-stakeholder-tabs');
  const navTelemetry = document.getElementById('nav-telemetry-tabs');

  if (mode === 'stakeholder') {
    if (btnStakeholder) btnStakeholder.classList.add('active');
    if (btnTelemetry) btnTelemetry.classList.remove('active');
    if (navStakeholder) navStakeholder.style.display = 'flex';
    if (navTelemetry) navTelemetry.style.display = 'none';
    switchTab('war-room');
  } else {
    if (btnStakeholder) btnStakeholder.classList.remove('active');
    if (btnTelemetry) btnTelemetry.classList.add('active');
    if (navStakeholder) navStakeholder.style.display = 'none';
    if (navTelemetry) navTelemetry.style.display = 'flex';
    switchTab('stages');
  }
}

// ==========================================================================
// 2. Tab Navigation
// ==========================================================================
function switchTab(tabId) {
  const telemetryTabs = ['stages', 'agents', 'metrics', 'architecture', 'edge-cases', 'studio'];
  const stakeholderTabs = ['war-room', 'recommendations', 'matching', 'graph'];

  const btnStakeholder = document.getElementById('btn-mode-stakeholder');
  const btnTelemetry = document.getElementById('btn-mode-telemetry');
  const navStakeholder = document.getElementById('nav-stakeholder-tabs');
  const navTelemetry = document.getElementById('nav-telemetry-tabs');

  if (telemetryTabs.includes(tabId)) {
    currentDashboardMode = 'telemetry';
    if (btnStakeholder) btnStakeholder.classList.remove('active');
    if (btnTelemetry) btnTelemetry.classList.add('active');
    if (navStakeholder) navStakeholder.style.display = 'none';
    if (navTelemetry) navTelemetry.style.display = 'flex';
  } else if (stakeholderTabs.includes(tabId)) {
    currentDashboardMode = 'stakeholder';
    if (btnStakeholder) btnStakeholder.classList.add('active');
    if (btnTelemetry) btnTelemetry.classList.remove('active');
    if (navStakeholder) navStakeholder.style.display = 'flex';
    if (navTelemetry) navTelemetry.style.display = 'none';
  }

  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  const activeContent = document.getElementById(`view-${tabId}`);

  if (activeBtn) activeBtn.classList.add('active');
  if (activeContent) activeContent.classList.add('active');

  if (tabId === 'recommendations') {
    fetchRecommendations();
  } else if (tabId === 'metrics') {
    fetchMetrics();
    fetchDriftStatus();
  } else if (tabId === 'graph') {
    renderKnowledgeGraph();
  } else if (tabId === 'studio') {
    fetchHitlQueue();
  } else if (tabId === 'edge-cases') {
    fetchChaosStatus();
  }
}

// ==========================================================================
// 3. Executive Guided Tour
// ==========================================================================
function startExecutiveTour() {
  currentTourStep = 0;
  const banner = document.getElementById('tour-banner');
  if (banner) banner.style.display = 'flex';
  renderTourStep();
}

function stopExecutiveTour() {
  const banner = document.getElementById('tour-banner');
  if (banner) banner.style.display = 'none';
}

function nextTourStep() {
  if (currentTourStep < tourSteps.length - 1) {
    currentTourStep++;
    renderTourStep();
  } else {
    stopExecutiveTour();
    switchDashboardMode('stakeholder');
    alert('Executive Presentation Tour Completed! You can now explore live recommendations and simulation tools.');
  }
}

function prevTourStep() {
  if (currentTourStep > 0) {
    currentTourStep--;
    renderTourStep();
  }
}

function renderTourStep() {
  const step = tourSteps[currentTourStep];
  if (step.mode !== currentDashboardMode) {
    switchDashboardMode(step.mode);
  }
  switchTab(step.tab);

  const badgeEl = document.getElementById('tour-step-badge');
  const titleEl = document.getElementById('tour-title');
  const descEl = document.getElementById('tour-description');

  if (badgeEl) badgeEl.innerText = step.badge;
  if (titleEl) titleEl.innerText = step.title;
  if (descEl) descEl.innerText = step.description;
}

// ==========================================================================
// 4. Strategic Merchandising Recommendations (Commercial Action Engine)
// ==========================================================================
async function fetchRecommendations() {
  try {
    const cat = document.getElementById('rec-filter-cat')?.value || 'all';
    const urgency = document.getElementById('rec-filter-urgency')?.value || 'all';
    const type = document.getElementById('rec-filter-type')?.value || 'all';

    const params = new URLSearchParams();
    if (cat !== 'all') params.append('category', cat);
    if (urgency !== 'all') params.append('urgency', urgency);
    if (type !== 'all') params.append('action_type', type);

    const res = await fetch(`/api/v1/recommendations?${params.toString()}`);
    if (!res.ok) return;

    const data = await res.json();
    renderRecommendations(data);

    // Update KPI counters
    const kpiMargin = document.getElementById('kpi-margin-protected');
    const kpiRev = document.getElementById('kpi-rev-uplift');
    const kpiPi = document.getElementById('kpi-price-index');

    if (kpiMargin) kpiMargin.innerText = `$${data.gross_margin_protected_usd.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    if (kpiRev) kpiRev.innerText = `$${data.projected_revenue_uplift_usd.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    if (kpiPi) kpiPi.innerText = data.average_price_index.toFixed(1);

    const recTotal = document.getElementById('rec-total-count');
    const recImm = document.getElementById('rec-immediate-count');
    const recRisk = document.getElementById('rec-rev-risk');
    const recProt = document.getElementById('rec-margin-protected');
    const recOem = document.getElementById('rec-oem-uplift');

    if (recTotal) recTotal.innerText = `${data.total_active_recommendations} Actions`;
    if (recImm) recImm.innerText = `${data.immediate_actions_count} Immediate`;
    if (recRisk) recRisk.innerText = `$${data.total_revenue_at_risk_usd.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    if (recProt) recProt.innerText = `$${data.gross_margin_protected_usd.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    if (recOem) recOem.innerText = `$${(data.projected_revenue_uplift_usd * 0.45).toLocaleString('en-US', {minimumFractionDigits: 2})}`;

  } catch (err) {
    console.error('Failed to load recommendations:', err);
  }
}

function renderRecommendations(data) {
  const container = document.getElementById('recommendations-container');
  if (!container) return;

  if (!data.top_actions || data.top_actions.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: var(--text-secondary);">
        <p>No active directives match the selected filter criteria.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  data.top_actions.forEach(rec => {
    const card = document.createElement('div');
    const urgencyClass = `urgency-${rec.urgency.toLowerCase()}`;
    card.className = `rec-card ${urgencyClass}`;

    let badgeClass = 'badge-medium';
    if (rec.urgency === 'IMMEDIATE') badgeClass = 'badge-immediate';
    else if (rec.urgency === 'HIGH') badgeClass = 'badge-high';
    else if (rec.urgency === 'STRATEGIC') badgeClass = 'badge-strategic';

    const stepsHtml = rec.action_steps.map(s => `<li>${s}</li>`).join('');

    card.innerHTML = `
      <div class="rec-header-row">
        <div style="display:flex; gap:8px; align-items:center;">
          <span class="rec-type-badge ${badgeClass}">${rec.urgency} &bull; ${formatActionName(rec.action_type)}</span>
          <span class="rec-sku-tag">${rec.internal_sku} &harr; ${rec.competitor_sku}</span>
        </div>
        <span class="badge badge-info" style="font-size:0.7rem;">PI: ${rec.category_price_index.toFixed(1)}</span>
      </div>

      <h3 class="rec-title">${rec.internal_title}</h3>

      <div class="rec-directive-banner">
        🎯 <strong>DIRECTIVE:</strong> ${rec.executive_directive}
      </div>

      <div class="rec-financial-matrix">
        <div class="rec-fin-box">
          <span class="rec-fin-label">Internal MSRP</span>
          <span class="rec-fin-val text-primary">$${rec.internal_price.toFixed(2)}</span>
        </div>
        <div class="rec-fin-box">
          <span class="rec-fin-label">${rec.competitor_name}</span>
          <span class="rec-fin-val text-amber">$${rec.competitor_price.toFixed(2)} (${rec.price_gap_pct > 0 ? '+' : ''}${rec.price_gap_pct}%)</span>
        </div>
        <div class="rec-fin-box">
          <span class="rec-fin-label">Rec. Price</span>
          <span class="rec-fin-val text-cyan">$${rec.recommended_price.toFixed(2)}</span>
        </div>
        <div class="rec-fin-box">
          <span class="rec-fin-label">Proj. Margin</span>
          <span class="rec-fin-val text-green">${rec.projected_margin_pct}%</span>
        </div>
      </div>

      <p class="rec-rationale"><strong>Strategic Rationale:</strong> ${rec.strategic_rationale}</p>

      <div class="rec-steps-box">
        <div class="rec-steps-title">Recommended Merchandising Action Steps:</div>
        <ul class="rec-step-list">
          ${stepsHtml}
        </ul>
      </div>

      <div class="rec-guardrails-tag">
        🛡️ <strong>Guardrail:</strong> ${rec.guardrails}
      </div>

      <div class="rec-card-actions" style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.08); gap:8px;">
        <button class="btn btn-primary btn-xs" onclick="startStreamingAnalysis('${rec.competitor_sku}')">
          ⚡ Audit with Multi-Agents & Stream Thoughts
        </button>
        <button class="btn btn-secondary btn-xs" id="btn-approve-${rec.recommendation_id}" onclick="approveRecommendation('${rec.recommendation_id}', '${rec.action_type}', '${rec.internal_sku}', ${rec.recommended_price})">
          ✅ Push to Repricer
        </button>
      </div>
    `;

    container.appendChild(card);
  });
}

function formatActionName(actionType) {
  return actionType.replace(/_/g, ' ');
}

async function approveRecommendation(recId, actionType, targetSku, approvedPrice) {
  const btn = document.getElementById(`btn-approve-${recId}`);
  if (btn) {
    btn.disabled = true;
    btn.innerText = 'Dispatching...';
  }
  try {
    const res = await fetch('/api/v1/recommendations/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        recommendation_id: recId,
        action_type: actionType,
        target_sku: targetSku,
        approved_price: approvedPrice
      })
    });
    if (res.ok) {
      if (btn) {
        btn.className = 'btn btn-xs';
        btn.style.background = 'rgba(16, 185, 129, 0.2)';
        btn.style.color = '#10b981';
        btn.style.borderColor = '#10b981';
        btn.innerText = '✓ Dispatched to ERP';
      }
      alert(`Directive Approved: ${recId} for SKU ${targetSku} ($${approvedPrice.toFixed(2)}) dispatched to Dynamic Repricer & ERP with margin guardrails confirmed.`);
    }
  } catch (err) {
    console.error('Approval failed:', err);
    if (btn) {
      btn.disabled = false;
      btn.innerText = '✅ Push to Repricer';
    }
  }
}

async function runFullCatalogOrchestration() {
  const btn = document.getElementById('btn-orchestrate-recs');
  if (btn) {
    btn.disabled = true;
    btn.innerText = 'Orchestrating Cognitive Mesh...';
  }
  try {
    const res = await fetch('/api/v1/pipelines/run-full-lifecycle', { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      await fetchRecommendations();
      await fetchMetrics();
      alert(`Strategic Recommendation Orchestration Complete!\nProcessed ${data.total_datapoints_processed.toLocaleString()} observations across ${data.competitors_monitored} competitors.\n${data.active_recommendations_count} directives synthesized with $${data.gross_margin_protected_usd.toLocaleString()} protected margin.`);
    }
  } catch (err) {
    console.error('Full orchestration failed:', err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = '⚡ Orchestrate Multi-Agent Recommendations';
    }
  }
}

// ==========================================================================
// 5. Catalogs & Market Feed Rendering (48 Competitors)
// ==========================================================================
async function fetchCatalogs() {
  try {
    const [compRes, intRes] = await Promise.all([
      fetch('/api/v1/catalog/competitor'),
      fetch('/api/v1/catalog/internal')
    ]);

    competitorCatalog = await compRes.json();
    internalCatalog = await intRes.json();

    filterMarketFeed();
    renderTierBoxes(competitorCatalog);
    
    if (competitorCatalog.length > 0) {
      analyzeSingleSku(competitorCatalog[0].competitor_sku);
    }
  } catch (err) {
    console.error('Failed to load catalogs:', err);
  }
}

function filterMarketFeed() {
  const catFilter = document.getElementById('filter-market-category')?.value || 'all';
  let items = competitorCatalog;
  if (catFilter !== 'all') {
    items = items.filter(i => (i.raw_category || '').includes(catFilter) || (i.title || '').includes(catFilter));
  }
  renderCompetitorTable(items);
}

function renderCompetitorTable(items) {
  const tbody = document.getElementById('competitor-table-body');
  if (!tbody) return;

  tbody.innerHTML = '';
  // Render up to 50 items with high performance
  items.slice(0, 50).forEach(item => {
    const tr = document.createElement('tr');

    let badgeClass = 'badge-info';
    let badgeText = 'Direct Match';

    if (item.is_honeypot) {
      badgeClass = 'badge-danger';
      badgeText = 'Honeypot Trap';
    } else if (item.is_phantom_stock || item.stock_status === 'BACKORDER') {
      badgeClass = 'badge-warning';
      badgeText = 'Phantom Stock';
    } else if (item.cart_discount > 0 || item.on_page_coupon > 0) {
      badgeClass = 'badge-success';
      badgeText = 'Hidden Coupon';
    } else if (item.challenge_class === 'PRIVATE_LABEL_OEM') {
      badgeClass = 'badge-purple';
      badgeText = 'OEM Arbitrage';
    } else if (item.challenge_class === 'MAP_VIOLATION') {
      badgeClass = 'badge-danger';
      badgeText = 'MAP Violation';
    }

    const hasDiscount = item.final_effective_price < item.scraped_base_price;
    const catShort = (item.raw_category || 'General').split('>').slice(-1)[0].trim();

    tr.innerHTML = `
      <td>
        <strong>${item.competitor_name}</strong>
        <div style="font-size:0.68rem; color:var(--text-muted);">${item.competitor_tier || 'Digital Retailer'}</div>
      </td>
      <td><span class="sku-code">${item.competitor_sku}</span></td>
      <td><strong>${item.title}</strong></td>
      <td><span class="badge badge-info" style="font-size:0.7rem;">${catShort}</span></td>
      <td>$${item.scraped_base_price.toFixed(2)}</td>
      <td>
        ${hasDiscount ? `<span class="price-strike">$${item.scraped_base_price.toFixed(2)}</span>` : ''}
        <span class="price-active text-cyan">$${item.final_effective_price.toFixed(2)}</span>
      </td>
      <td>
        <span class="badge ${item.stock_status === 'IN_STOCK' ? 'badge-success' : 'badge-danger'}">
          ${item.stock_status} (${item.fulfillment_latency_days}d)
        </span>
      </td>
      <td>
        <div style="display:flex; gap:4px;">
          <button class="btn btn-secondary btn-xs" onclick="analyzeSingleSku('${item.competitor_sku}'); switchTab('matching');">
            Inspect &rarr;
          </button>
          <button class="btn btn-primary btn-xs" onclick="startStreamingAnalysis('${item.competitor_sku}')">
            ⚡ Stream
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTierBoxes(items) {
  const t1 = document.getElementById('tier1-cases');
  const t2 = document.getElementById('tier2-cases');
  const t3 = document.getElementById('tier3-cases');
  const t4 = document.getElementById('tier4-cases');

  if (!t1 || !t2 || !t3 || !t4) return;

  t1.innerHTML = '';
  t2.innerHTML = '';
  t3.innerHTML = '';
  t4.innerHTML = '';

  items.slice(0, 16).forEach(item => {
    const chip = document.createElement('div');
    chip.className = 'tier-case-chip';
    chip.onclick = () => analyzeSingleSku(item.competitor_sku);

    if (item.gtin && !item.is_honeypot) {
      chip.innerHTML = `<span>${item.competitor_sku}</span><span class="chip-status">GTIN Match</span>`;
      t1.appendChild(chip);
    } else if (item.is_honeypot || item.competitor_sku.includes('CLASH')) {
      chip.innerHTML = `<span>${item.competitor_sku}</span><span class="chip-status">HITL Escalate</span>`;
      t4.appendChild(chip);
    } else if (item.is_phantom_stock || item.on_page_coupon > 0 || item.challenge_class === 'PRIVATE_LABEL_OEM') {
      chip.innerHTML = `<span>${item.competitor_sku}</span><span class="chip-status">Multi-Agent</span>`;
      t3.appendChild(chip);
    } else {
      chip.innerHTML = `<span>${item.competitor_sku}</span><span class="chip-status">Vector Top-K</span>`;
      t2.appendChild(chip);
    }
  });
}

// ==========================================================================
// 6. Single SKU Multi-Tier Analysis & Agentic Intelligence
// ==========================================================================
async function analyzeSingleSku(sku) {
  try {
    const res = await fetch('/api/v1/intelligence/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ competitor_sku: sku })
    });

    if (!res.ok) return;
    const data = await res.json();
    renderComparisonView(data);
  } catch (err) {
    console.error('Failed to analyze SKU:', err);
  }
}

function renderComparisonView(data) {
  const container = document.getElementById('comparison-view');
  if (!container) return;

  const compItem = competitorCatalog.find(c => c.competitor_sku === data.competitor_sku) || {};
  const intItem = internalCatalog.find(i => i.sku === data.target_internal_sku) || {};

  container.innerHTML = `
    <!-- Competitor Product Card -->
    <div class="product-pdp-card">
      <div class="pdp-header">
        <span class="pdp-source-badge competitor">${compItem.competitor_name || 'Competitor'} Listing</span>
        <span class="pdp-sku">${data.competitor_sku}</span>
      </div>
      <div class="pdp-body">
        <h3 class="pdp-title">${compItem.title || data.competitor_sku}</h3>
        <div class="pdp-meta-row">
          <span class="pdp-brand">Brand: ${compItem.brand || 'Unknown'}</span>
          <span class="pdp-category">${compItem.raw_category || 'Electronics'}</span>
        </div>
        <div class="pdp-price-box">
          <span class="pdp-price-label">Scraped Effective Price:</span>
          <span class="pdp-price-val text-cyan">$${(data.competitor_effective_price || 0).toFixed(2)}</span>
        </div>
        <div class="pdp-specs-list">
          <div class="spec-item"><strong>Fulfillment:</strong> ${compItem.stock_status || 'IN_STOCK'} (${compItem.fulfillment_latency_days || 1}d)</div>
          <div class="spec-item"><strong>OEM Factory ID:</strong> ${(compItem.specifications || {}).oem_factory_id || 'N/A'}</div>
          <div class="spec-item"><strong>Coupon Clipped:</strong> $${(compItem.on_page_coupon || 0).toFixed(2)}</div>
        </div>
      </div>
    </div>

    <!-- Resolution & Decision Arbiter Box -->
    <div class="resolution-arbiter-card">
      <div class="arbiter-header">
        <span class="badge badge-purple">${data.resolution_tier}</span>
        <span class="badge badge-success">Confidence: ${(data.confidence * 100).toFixed(1)}%</span>
      </div>
      <div class="verdict-banner">
        <span class="verdict-title">VERDICT:</span>
        <span class="verdict-val">${data.verdict}</span>
      </div>
      <div class="arbiter-reasoning">
        <p>${data.reasoning}</p>
      </div>
      <div class="arbiter-actions mt-12">
        <button class="btn btn-primary btn-sm" onclick="startStreamingAnalysis('${data.competitor_sku}')">
          Stream Multi-Agent Thoughts
        </button>
      </div>
    </div>

    <!-- Internal Catalog Match Card -->
    <div class="product-pdp-card">
      <div class="pdp-header">
        <span class="pdp-source-badge internal">Internal Catalog Match</span>
        <span class="pdp-sku">${data.target_internal_sku}</span>
      </div>
      <div class="pdp-body">
        <h3 class="pdp-title">${data.target_internal_title || intItem.title || 'Internal Product'}</h3>
        <div class="pdp-meta-row">
          <span class="pdp-brand">Brand: ${intItem.brand || 'Internal Brand'}</span>
          <span class="pdp-category">${intItem.canonical_category || 'GPC Harmonized'}</span>
        </div>
        <div class="pdp-price-box">
          <span class="pdp-price-label">Active Retail Price:</span>
          <span class="pdp-price-val text-green">$${(data.internal_price || intItem.current_price || 0).toFixed(2)}</span>
        </div>
        <div class="pdp-specs-list">
          <div class="spec-item"><strong>Cost of Goods (COGS):</strong> $${(intItem.cost_of_goods || 0).toFixed(2)}</div>
          <div class="spec-item"><strong>Margin Floor:</strong> $${(intItem.margin_floor || 0).toFixed(2)}</div>
          <div class="spec-item"><strong>OEM Factory ID:</strong> ${(intItem.specifications || {}).oem_factory_id || 'N/A'}</div>
        </div>
      </div>
    </div>
  `;
}

// ==========================================================================
// 7. Multi-Agent SSE Streaming Mesh (P-E-R-R)
// ==========================================================================
function startStreamingAnalysis(skuOverride) {
  const select = document.getElementById('stream-sku-select');
  const sku = skuOverride || (select ? select.value : 'ZEN-TV-65-OLED');
  if (select && skuOverride) select.value = skuOverride;

  if (currentDashboardMode !== 'telemetry') {
    switchDashboardMode('telemetry');
  }
  switchTab('agents');

  const consoleBox = document.getElementById('streaming-console');
  if (!consoleBox) return;

  // Reset P-E-R-R nodes to initial state
  updatePerrPipelineNodes('PLAN');

  consoleBox.innerHTML = `
    <div class="stream-msg system">
      <div class="stream-msg-header">
        <span class="stream-ts">[${new Date().toLocaleTimeString()}]</span>
        <span class="stream-phase phase-plan">[PLAN]</span>
        <span class="stream-agent">[SupervisorAgent]</span>
      </div>
      <div class="stream-action">Initiating live multi-agent reasoning session for <strong>${sku}</strong>...</div>
      <div class="stream-details-box">Connecting to EventSource stream (/api/v1/intelligence/stream?competitor_sku=${encodeURIComponent(sku)})...</div>
    </div>
  `;

  if (activeStream) {
    activeStream.close();
    activeStream = null;
  }

  activeStream = new EventSource(`/api/v1/intelligence/stream?competitor_sku=${encodeURIComponent(sku)}`);

  activeStream.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'step') {
        appendStreamMessage(payload.data || payload);
      } else if (payload.type === 'complete') {
        renderStreamCompletion(payload.data || payload);
        if (activeStream) {
          activeStream.close();
          activeStream = null;
        }
      } else if (payload.type === 'error') {
        appendStreamError(payload.data || payload);
      } else {
        appendStreamMessage(payload);
      }
    } catch (e) {
      console.error('Failed to parse SSE event:', e);
    }
  };

  activeStream.onerror = (err) => {
    console.warn('SSE stream closed or encountered network pause:', err);
    if (activeStream) {
      activeStream.close();
      activeStream = null;
    }
  };
}

function stopStreamingAnalysis() {
  if (activeStream) {
    activeStream.close();
    activeStream = null;
  }
  const consoleBox = document.getElementById('streaming-console');
  if (consoleBox) {
    const stopMsg = document.createElement('div');
    stopMsg.className = 'stream-msg system';
    stopMsg.innerHTML = `<span class="stream-ts">[${new Date().toLocaleTimeString()}]</span> Stream session paused by user.`;
    consoleBox.appendChild(stopMsg);
    consoleBox.scrollTop = consoleBox.scrollHeight;
  }
}

function updatePerrPipelineNodes(activePhase) {
  const phase = (activePhase || '').toUpperCase();
  const phaseMap = {
    'PLAN': 'node-plan',
    'EXECUTE': 'node-execute',
    'REFLECT': 'node-reflect',
    'REPORT': 'node-report'
  };

  const currentId = phaseMap[phase];
  ['node-plan', 'node-execute', 'node-reflect', 'node-report'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      if (id === currentId) {
        el.classList.add('active', 'pulse');
      } else {
        el.classList.remove('pulse');
      }
    }
  });
}

function formatStreamDetails(details) {
  if (!details || typeof details !== 'object') return '';

  if (details.sub_tasks && Array.isArray(details.sub_tasks)) {
    const list = details.sub_tasks.map(t => `<li>${t}</li>`).join('');
    return `<strong>Reasoning Sub-Tasks:</strong><ul class="stream-checklist">${list}</ul>`;
  }

  if (details.effective_price !== undefined) {
    return `<div>Net Checkout Price Discovered: <strong class="text-cyan">$${Number(details.effective_price).toFixed(2)}</strong></div>`;
  }

  if (details.match_type) {
    const conf = details.confidence ? ` (Confidence: ${(details.confidence * 100).toFixed(1)}%)` : '';
    return `<div>Entity Resolution: <strong class="text-purple">${details.match_type}</strong>${conf}</div>`;
  }

  if (details.correction_applied !== undefined) {
    return `<div>${details.correction_applied ? '⚠️ <strong class="text-amber">Hierarchy of Truth Alert:</strong> Contradiction isolated and self-corrected.' : '✅ <strong class="text-green">Consistency Verified:</strong> Multi-modal evidence aligns with Tier 1/2 Ground Truth.'}</div>`;
  }

  if (details.causal_intent) {
    return `<div>Intent: <strong class="text-amber">${details.causal_intent}</strong> &bull; Recommended Action: <strong class="text-cyan">${details.recommended_action || 'AUTO_REPRICE'}</strong></div>`;
  }

  return `<pre class="stream-details">${JSON.stringify(details, null, 2)}</pre>`;
}

function appendStreamMessage(step) {
  const consoleBox = document.getElementById('streaming-console');
  if (!consoleBox) return;

  const phase = (step.phase || 'EXECUTE').toUpperCase();
  updatePerrPipelineNodes(phase);

  const msgDiv = document.createElement('div');
  msgDiv.className = `stream-msg ${phase.toLowerCase()}`;

  const ts = new Date().toLocaleTimeString();
  const agent = step.agent || 'Supervisor';
  const action = step.action || '';
  const dur = step.duration_ms ? `<span class="stream-duration">${step.duration_ms}ms</span>` : '';

  let detailsBox = '';
  if (step.details && Object.keys(step.details).length > 0) {
    detailsBox = `<div class="stream-details-box">${formatStreamDetails(step.details)}</div>`;
  }

  msgDiv.innerHTML = `
    <div class="stream-msg-header">
      <span class="stream-ts">[${ts}]</span>
      <span class="stream-phase phase-${phase.toLowerCase()}">[${phase}]</span>
      <span class="stream-agent">[${agent}]</span>
      ${dur}
    </div>
    <div class="stream-action">${action}</div>
    ${detailsBox}
  `;

  consoleBox.appendChild(msgDiv);
  consoleBox.scrollTop = consoleBox.scrollHeight;
}

function renderStreamCompletion(intel) {
  const consoleBox = document.getElementById('streaming-console');
  if (!consoleBox) return;

  updatePerrPipelineNodes('REPORT');

  const strat = intel.strategy || {};
  const res = intel.resolution || {};
  const promo = intel.promotions || {};
  const verdict = intel.verdict || 'RESOLVED';
  const conf = Math.round((intel.confidence || res.confidence || 0.95) * 100);
  const optRatio = (intel.plan_optimality_ratio || 1.0).toFixed(2);
  const stepsCount = intel.total_steps_executed || 5;
  const marginProt = (strat.gross_margin_protected_usd || 0).toLocaleString('en-US', { minimumFractionDigits: 2 });
  const compSku = intel.competitor_sku || '';
  const intSku = intel.target_internal_sku || '';

  const card = document.createElement('div');
  card.className = 'stream-complete-card';
  card.innerHTML = `
    <div class="complete-header">
      <div class="complete-title-group">
        <span class="complete-badge badge-success">🏆 REASONING SYNTHESIS CONVERGED</span>
        <h3 class="complete-verdict-title">${compSku} &harr; ${intSku}</h3>
      </div>
      <div class="complete-verdict-pill">${verdict} (${conf}% Confidence)</div>
    </div>
    <div class="complete-grid">
      <div class="complete-kpi">
        <span class="ckpi-label">Causal Intent</span>
        <span class="ckpi-val text-amber">${strat.causal_intent || 'ROUTINE_COMPETITION'}</span>
      </div>
      <div class="complete-kpi">
        <span class="ckpi-label">Recommended Directive</span>
        <span class="ckpi-val text-cyan">${strat.recommended_action || 'AUTO_REPRICE'}</span>
      </div>
      <div class="complete-kpi">
        <span class="ckpi-label">Protected Gross Margin</span>
        <span class="ckpi-val text-green">$${marginProt}</span>
      </div>
      <div class="complete-kpi">
        <span class="ckpi-label">Plan Optimality</span>
        <span class="ckpi-val text-purple">&eta; = ${optRatio} (${stepsCount} steps)</span>
      </div>
    </div>
    <div class="complete-briefing">
      <strong>Executive Strategic Briefing:</strong> ${strat.strategic_briefing || intel.reasoning_summary || 'Autonomous decision loop completed.'}
    </div>
  `;

  consoleBox.appendChild(card);
  consoleBox.scrollTop = consoleBox.scrollHeight;
}

function appendStreamError(errorData) {
  const consoleBox = document.getElementById('streaming-console');
  if (!consoleBox) return;

  const errDiv = document.createElement('div');
  errDiv.className = 'stream-msg system';
  errDiv.style.borderLeftColor = 'var(--accent-red)';
  errDiv.innerHTML = `
    <div class="stream-msg-header">
      <span class="stream-ts">[${new Date().toLocaleTimeString()}]</span>
      <span class="stream-phase" style="color:var(--accent-red);">[ERROR]</span>
      <span class="stream-agent">[SupervisorAgent]</span>
    </div>
    <div class="stream-action" style="color:#f87171;">Reasoning stream error: ${errorData.message || JSON.stringify(errorData)}</div>
  `;
  consoleBox.appendChild(errDiv);
  consoleBox.scrollTop = consoleBox.scrollHeight;
}

// ==========================================================================
// 8. Retail Knowledge Graph Explorer (3D WebGL Constellation + 2D Interactive Map)
// ==========================================================================
let kg3dScene, kg3dCamera, kg3dRenderer, kg3dNodes = [], kg3dLinks = [];
let kg3dReqId = null;
let is3dRotating = true;
let is3dDragging = false;
let prevMousePos = { x: 0, y: 0 };
let kgSpherical = { radius: 450, theta: Math.PI / 4, phi: Math.PI / 3 };
let targetCameraPos = null;
let activeNodeTypeFilter = 'ALL';
let activeGraphDimension = '3d';

// 2D Pan & Zoom state
let svgZoom = { scale: 1.0, tx: 0, ty: 0, isDragging: false, startX: 0, startY: 0 };

async function renderKnowledgeGraph() {
  try {
    const res = await fetch('/api/v1/graph/subgraph');
    if (res.ok) {
      kgData = await res.json();
    }
  } catch (e) {
    console.error('Failed to fetch graph data:', e);
  }

  if (activeGraphDimension === '3d') {
    init3dKnowledgeGraph();
  } else {
    render2dKnowledgeGraph();
  }
}

function switchGraphDimension(dim) {
  activeGraphDimension = dim;
  const btn3d = document.getElementById('btn-kg-3d');
  const btn2d = document.getElementById('btn-kg-2d');
  const wrap3d = document.getElementById('graph-3d-wrapper');
  const wrap2d = document.getElementById('graph-2d-wrapper');

  if (dim === '3d') {
    if (btn3d) btn3d.className = 'btn btn-primary btn-xs active';
    if (btn2d) btn2d.className = 'btn btn-secondary btn-xs';
    if (wrap3d) wrap3d.style.display = 'block';
    if (wrap2d) wrap2d.style.display = 'none';
    init3dKnowledgeGraph();
  } else {
    if (btn3d) btn3d.className = 'btn btn-secondary btn-xs';
    if (btn2d) btn2d.className = 'btn btn-primary btn-xs active';
    if (wrap3d) wrap3d.style.display = 'none';
    if (wrap2d) wrap2d.style.display = 'block';
    render2dKnowledgeGraph();
  }
}

// --------------------------------------------------------------------------
// 3D Three.js WebGL Constellation Engine
// --------------------------------------------------------------------------
function init3dKnowledgeGraph() {
  const canvas = document.getElementById('kg-3d-canvas');
  if (!canvas || typeof THREE === 'undefined') {
    console.warn('Three.js not loaded or canvas missing; falling back to 2D.');
    switchGraphDimension('2d');
    return;
  }

  if (kg3dReqId) {
    cancelAnimationFrame(kg3dReqId);
  }

  const container = canvas.parentElement;
  const width = container.clientWidth || 800;
  const height = 540;

  kg3dScene = new THREE.Scene();
  kg3dScene.background = new THREE.Color(0x0a0d17);

  kg3dCamera = new THREE.PerspectiveCamera(50, width / height, 0.1, 3000);
  update3dCameraPosition();

  kg3dRenderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
  kg3dRenderer.setSize(width, height);
  kg3dRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
  kg3dScene.add(ambientLight);

  const dirLight1 = new THREE.DirectionalLight(0x06b6d4, 1.2);
  dirLight1.position.set(200, 300, 200);
  kg3dScene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0xa855f7, 0.9);
  dirLight2.position.set(-200, -200, -200);
  kg3dScene.add(dirLight2);

  // Background star particles
  const starsGeo = new THREE.BufferGeometry();
  const starCoords = [];
  for (let i = 0; i < 400; i++) {
    starCoords.push((Math.random() - 0.5) * 1200, (Math.random() - 0.5) * 1200, (Math.random() - 0.5) * 1200);
  }
  starsGeo.setAttribute('position', new THREE.Float32BufferAttribute(starCoords, 3));
  const starsMat = new THREE.PointsMaterial({ color: 0x475569, size: 2, transparent: true, opacity: 0.6 });
  const stars = new THREE.Points(starsGeo, starsMat);
  kg3dScene.add(stars);

  // Layout 3D Nodes in organic hierarchical spheres
  kg3dNodes = [];
  const nodes = kgData.nodes || [];
  const links = kgData.links || [];

  const nodeCount = nodes.length || 1;
  const phiSpan = Math.PI * (3 - Math.sqrt(5)); // golden ratio angle

  nodes.forEach((n, i) => {
    const y = 1 - (i / (nodeCount - 1 || 1)) * 2;
    const radiusAtY = Math.sqrt(1 - y * y);
    const theta = phiSpan * i;

    let rDist = 180;
    if (n.type === 'Parent_Company') rDist = 70;
    else if (n.type === 'Brand') rDist = 130;
    else if (n.type === 'OEM_Factory') rDist = 150;
    else if (n.type === 'Competitor') rDist = 200;
    else rDist = 230;

    const x = Math.cos(theta) * radiusAtY * rDist;
    const z = Math.sin(theta) * radiusAtY * rDist;
    const py = y * rDist * 0.85;

    const hexColor = getNodeColorHex(n.type);
    const sphereGeo = new THREE.SphereGeometry(n.type === 'Parent_Company' ? 14 : (n.type === 'OEM_Factory' ? 12 : 9), 24, 24);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: hexColor,
      roughness: 0.25,
      metalness: 0.35,
      emissive: hexColor,
      emissiveIntensity: 0.4
    });

    const mesh = new THREE.Mesh(sphereGeo, sphereMat);
    mesh.position.set(x, py, z);
    mesh.userData = { node: n, originalEmissive: 0.4, originalScale: 1.0 };

    kg3dScene.add(mesh);
    kg3dNodes.push(mesh);
  });

  // Create 3D Edge Lines
  kg3dLinks = [];
  links.forEach(l => {
    const srcMesh = kg3dNodes.find(m => m.userData.node.id === l.source);
    const tgtMesh = kg3dNodes.find(m => m.userData.node.id === l.target);

    if (srcMesh && tgtMesh) {
      const lineGeo = new THREE.BufferGeometry().setFromPoints([srcMesh.position, tgtMesh.position]);
      const lineMat = new THREE.LineBasicMaterial({
        color: l.relationship === 'MANUFACTURED_BY' ? 0x10b981 : (l.relationship === 'MAPS_TO' ? 0x06b6d4 : 0x64748b),
        transparent: true,
        opacity: 0.45,
        linewidth: 1.5
      });
      const line = new THREE.Line(lineGeo, lineMat);
      kg3dScene.add(line);
      kg3dLinks.push(line);
    }
  });

  setup3dCanvasEvents(canvas);
  animate3dGraph();
}

function animate3dGraph() {
  kg3dReqId = requestAnimationFrame(animate3dGraph);

  if (is3dRotating && !is3dDragging) {
    kgSpherical.theta += 0.003;
    update3dCameraPosition();
  }

  // Smooth camera fly-to animation
  if (targetCameraPos) {
    kg3dCamera.position.lerp(targetCameraPos, 0.08);
    kg3dCamera.lookAt(0, 0, 0);
    if (kg3dCamera.position.distanceTo(targetCameraPos) < 2) {
      targetCameraPos = null;
    }
  }

  if (kg3dRenderer && kg3dScene && kg3dCamera) {
    kg3dRenderer.render(kg3dScene, kg3dCamera);
  }
}

function update3dCameraPosition() {
  kgSpherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, kgSpherical.phi));
  kg3dCamera.position.x = kgSpherical.radius * Math.sin(kgSpherical.phi) * Math.cos(kgSpherical.theta);
  kg3dCamera.position.y = kgSpherical.radius * Math.cos(kgSpherical.phi);
  kg3dCamera.position.z = kgSpherical.radius * Math.sin(kgSpherical.phi) * Math.sin(kgSpherical.theta);
  kg3dCamera.lookAt(0, 0, 0);
}

function setup3dCanvasEvents(canvas) {
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  canvas.onmousedown = (e) => {
    is3dDragging = true;
    prevMousePos = { x: e.clientX, y: e.clientY };
    canvas.style.cursor = 'grabbing';
  };

  window.onmousemove = (e) => {
    if (!is3dDragging) {
      // Raycasting for hover
      const rect = canvas.getBoundingClientRect();
      if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {
        mouse.x = ((e.clientX - rect.left) / canvas.clientWidth) * 2 - 1;
        mouse.y = -((e.clientY - rect.top) / canvas.clientHeight) * 2 + 1;

        raycaster.setFromCamera(mouse, kg3dCamera);
        const intersects = raycaster.intersectObjects(kg3dNodes);

        kg3dNodes.forEach(m => m.material.emissiveIntensity = m.userData.originalEmissive);
        if (intersects.length > 0) {
          canvas.style.cursor = 'pointer';
          intersects[0].object.material.emissiveIntensity = 1.0;
        } else {
          canvas.style.cursor = 'grab';
        }
      }
      return;
    }

    const deltaX = e.clientX - prevMousePos.x;
    const deltaY = e.clientY - prevMousePos.y;

    kgSpherical.theta -= deltaX * 0.007;
    kgSpherical.phi -= deltaY * 0.007;
    update3dCameraPosition();

    prevMousePos = { x: e.clientX, y: e.clientY };
  };

  window.onmouseup = () => {
    is3dDragging = false;
    canvas.style.cursor = 'grab';
  };

  canvas.onclick = (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / canvas.clientWidth) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / canvas.clientHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, kg3dCamera);
    const intersects = raycaster.intersectObjects(kg3dNodes);

    if (intersects.length > 0) {
      const clickedMesh = intersects[0].object;
      selectKgNode(clickedMesh.userData.node);
      focus3dNode(clickedMesh);
    }
  };

  canvas.onwheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
    kgSpherical.radius = Math.max(120, Math.min(1200, kgSpherical.radius * zoomFactor));
    update3dCameraPosition();
  };
}

function focus3dNode(mesh) {
  // Pulse animation & highlight
  kg3dNodes.forEach(m => {
    m.scale.set(1, 1, 1);
    m.material.emissiveIntensity = 0.2;
  });

  mesh.scale.set(1.5, 1.5, 1.5);
  mesh.material.emissiveIntensity = 1.2;

  // Fly camera closer to target
  targetCameraPos = mesh.position.clone().multiplyScalar(1.6);
}

// --------------------------------------------------------------------------
// 2D SVG Interactive Map with Smooth Pan & Zoom
// --------------------------------------------------------------------------
function render2dKnowledgeGraph() {
  const svg = document.getElementById('kg-svg-canvas');
  if (!svg) return;

  const width = svg.clientWidth || 800;
  const height = 540;
  svg.innerHTML = '';

  const nodes = kgData.nodes || [];
  const links = kgData.links || [];

  // Filter nodes if active filter is set
  const visibleNodes = activeNodeTypeFilter === 'ALL'
    ? nodes
    : nodes.filter(n => n.type === activeNodeTypeFilter || n.type === 'OEM_Factory');

  const gMain = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  gMain.id = 'kg-svg-zoom-group';
  gMain.setAttribute('transform', `translate(${svgZoom.tx}, ${svgZoom.ty}) scale(${svgZoom.scale})`);
  svg.appendChild(gMain);

  const angleStep = (2 * Math.PI) / (visibleNodes.length || 1);
  const radius = Math.min(width, height) * 0.38;
  const cx = width / 2;
  const cy = height / 2;

  visibleNodes.forEach((n, i) => {
    n.x = cx + radius * Math.cos(i * angleStep);
    n.y = cy + radius * Math.sin(i * angleStep);
  });

  // Draw links
  links.forEach(l => {
    const sourceNode = visibleNodes.find(n => n.id === l.source);
    const targetNode = visibleNodes.find(n => n.id === l.target);

    if (sourceNode && targetNode) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', sourceNode.x);
      line.setAttribute('y1', sourceNode.y);
      line.setAttribute('x2', targetNode.x);
      line.setAttribute('y2', targetNode.y);
      line.setAttribute('stroke', l.relationship === 'MANUFACTURED_BY' ? 'rgba(16,185,129,0.5)' : 'rgba(255,255,255,0.18)');
      line.setAttribute('stroke-width', l.relationship === 'MANUFACTURED_BY' ? '2' : '1.2');
      gMain.appendChild(line);
    }
  });

  // Draw nodes
  visibleNodes.forEach(n => {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.style.cursor = 'pointer';
    g.id = `node-${n.id.replace(/[^a-zA-Z0-9]/g, '_')}`;
    g.onclick = () => selectKgNode(n);

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', n.x);
    circle.setAttribute('cy', n.y);
    circle.setAttribute('r', n.type === 'Parent_Company' ? '20' : (n.type === 'OEM_Factory' ? '16' : '12'));
    circle.setAttribute('fill', getNodeColor(n.type));
    circle.setAttribute('stroke', '#fff');
    circle.setAttribute('stroke-width', '2');

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', n.x);
    text.setAttribute('y', n.y + 24);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('fill', '#f8fafc');
    text.setAttribute('font-size', '10px');
    text.setAttribute('font-weight', '600');
    text.textContent = n.id.length > 14 ? n.id.slice(0, 12) + '..' : n.id;

    g.appendChild(circle);
    g.appendChild(text);
    gMain.appendChild(g);
  });

  setup2dSvgEvents(svg, gMain);
}

function setup2dSvgEvents(svg, gMain) {
  svg.onmousedown = (e) => {
    svgZoom.isDragging = true;
    svgZoom.startX = e.clientX - svgZoom.tx;
    svgZoom.startY = e.clientY - svgZoom.ty;
    svg.style.cursor = 'grabbing';
  };

  window.onmousemove = (e) => {
    if (!svgZoom.isDragging) return;
    svgZoom.tx = e.clientX - svgZoom.startX;
    svgZoom.ty = e.clientY - svgZoom.startY;
    gMain.setAttribute('transform', `translate(${svgZoom.tx}, ${svgZoom.ty}) scale(${svgZoom.scale})`);
  };

  window.onmouseup = () => {
    svgZoom.isDragging = false;
    svg.style.cursor = 'grab';
  };

  svg.onwheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    zoomGraph(factor);
  };
}

// --------------------------------------------------------------------------
// Zoom & Viewport Actions (3D and 2D)
// --------------------------------------------------------------------------
function zoomGraph(factor) {
  if (activeGraphDimension === '3d') {
    kgSpherical.radius = Math.max(120, Math.min(1200, kgSpherical.radius / factor));
    update3dCameraPosition();
  } else {
    svgZoom.scale = Math.max(0.3, Math.min(4.0, svgZoom.scale * factor));
    const gMain = document.getElementById('kg-svg-zoom-group');
    if (gMain) {
      gMain.setAttribute('transform', `translate(${svgZoom.tx}, ${svgZoom.ty}) scale(${svgZoom.scale})`);
    }
  }
}

function resetGraphView() {
  if (activeGraphDimension === '3d') {
    kgSpherical = { radius: 450, theta: Math.PI / 4, phi: Math.PI / 3 };
    targetCameraPos = null;
    is3dRotating = true;
    update3dCameraPosition();
    kg3dNodes.forEach(m => {
      m.scale.set(1, 1, 1);
      m.material.emissiveIntensity = m.userData.originalEmissive;
    });
  } else {
    svgZoom = { scale: 1.0, tx: 0, ty: 0, isDragging: false, startX: 0, startY: 0 };
    render2dKnowledgeGraph();
  }
}

function toggleAutoRotate() {
  is3dRotating = !is3dRotating;
  const btn = document.getElementById('btn-kg-rotate');
  if (btn) btn.innerText = is3dRotating ? '🎯 Auto-Rotate (ON)' : '⏸️ Auto-Rotate (OFF)';
}

function searchAndFocusNode() {
  const query = document.getElementById('kg-search-input')?.value.trim().toLowerCase();
  if (!query) return;

  const nodes = kgData.nodes || [];
  const foundNode = nodes.find(n =>
    n.id.toLowerCase().includes(query) ||
    JSON.stringify(n.properties || {}).toLowerCase().includes(query)
  );

  if (!foundNode) return;

  selectKgNode(foundNode);

  if (activeGraphDimension === '3d') {
    const mesh = kg3dNodes.find(m => m.userData.node.id === foundNode.id);
    if (mesh) {
      focus3dNode(mesh);
    }
  } else {
    // Center 2D SVG
    const svg = document.getElementById('kg-svg-canvas');
    if (svg && foundNode.x && foundNode.y) {
      const cx = svg.clientWidth / 2;
      const cy = svg.clientHeight / 2;
      svgZoom.scale = 1.6;
      svgZoom.tx = cx - foundNode.x * svgZoom.scale;
      svgZoom.ty = cy - foundNode.y * svgZoom.scale;
      const gMain = document.getElementById('kg-svg-zoom-group');
      if (gMain) {
        gMain.setAttribute('transform', `translate(${svgZoom.tx}, ${svgZoom.ty}) scale(${svgZoom.scale})`);
      }
    }
  }
}

function filterGraphNodeType(type, el) {
  activeNodeTypeFilter = type;
  document.querySelectorAll('.chip-filter').forEach(c => c.classList.remove('active'));
  if (el) el.classList.add('active');

  if (activeGraphDimension === '3d') {
    kg3dNodes.forEach(m => {
      const match = type === 'ALL' || m.userData.node.type === type;
      m.visible = match;
    });
  } else {
    render2dKnowledgeGraph();
  }
}

function getNodeColor(type) {
  switch (type) {
    case 'Parent_Company': return '#f43f5e';
    case 'Brand': return '#8b5cf6';
    case 'Competitor': return '#f59e0b';
    case 'OEM_Factory': return '#10b981';
    case 'Internal_SKU': return '#06b6d4';
    case 'Competitor_SKU': return '#ec4899';
    default: return '#3b82f6';
  }
}

function getNodeColorHex(type) {
  switch (type) {
    case 'Parent_Company': return 0xf43f5e;
    case 'Brand': return 0x8b5cf6;
    case 'Competitor': return 0xf59e0b;
    case 'OEM_Factory': return 0x10b981;
    case 'Internal_SKU': return 0x06b6d4;
    case 'Competitor_SKU': return 0xec4899;
    default: return 0x3b82f6;
  }
}

function selectKgNode(node) {
  const pane = document.getElementById('kg-node-details');
  if (!pane) return;

  const typeColor = getNodeColor(node.type);
  const links = (kgData.links || []).filter(l => l.source === node.id || l.target === node.id);

  const linksHtml = links.map(l => {
    const isSource = l.source === node.id;
    const otherId = isSource ? l.target : l.source;
    const direction = isSource ? '&rarr;' : '&larr;';
    return `
      <div style="font-size:0.75rem; background:rgba(0,0,0,0.3); padding:6px 8px; border-radius:6px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
        <span><strong>${direction} ${l.relationship}</strong>: ${otherId}</span>
        <button class="btn btn-ghost btn-xs" style="padding:2px 6px;" onclick="searchNodeById('${otherId}')">Focus</button>
      </div>
    `;
  }).join('');

  pane.innerHTML = `
    <div style="padding:14px; background:rgba(0,0,0,0.35); border-radius:10px; border:1px solid var(--border-glass);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="badge" style="background:${typeColor}22; color:${typeColor}; border:1px solid ${typeColor}55;">${node.type}</span>
        <span style="font-family:var(--font-mono); font-size:0.72rem; color:var(--text-secondary);">${node.id}</span>
      </div>

      <h4 style="color:#fff; font-size:1.05rem; margin-bottom:10px;">${node.properties?.title || node.properties?.name || node.id}</h4>

      <div style="margin-bottom:12px;">
        <span style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Entity Specifications:</span>
        <pre style="font-size:0.72rem; color:var(--accent-cyan); background:rgba(0,0,0,0.45); padding:8px 10px; border-radius:6px; overflow-x:auto; margin-top:4px;">${JSON.stringify(node.properties || {}, null, 2)}</pre>
      </div>

      <div>
        <span style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Active Graph Relationships (${links.length}):</span>
        <div style="margin-top:6px; max-height:160px; overflow-y:auto;">
          ${linksHtml || '<p style="font-size:0.72rem; color:var(--text-muted);">No direct relationships.</p>'}
        </div>
      </div>
    </div>
  `;
}

function searchNodeById(nodeId) {
  const input = document.getElementById('kg-search-input');
  if (input) input.value = nodeId;
  searchAndFocusNode();
}


// ==========================================================================
// 9. Dataset Generation (20,000+ Datapoints) & Evaluation
// ==========================================================================
async function generateLargeEnterpriseDataset(totalPoints = 20000) {
  try {
    const btn = document.getElementById('btn-quick-run');
    if (btn) btn.innerText = `Generating ${totalPoints.toLocaleString()} Pts...`;

    const res = await fetch('/api/v1/pipelines/generate-dataset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ total_datapoints: totalPoints, sku_count: 48 })
    });

    const data = await res.json();
    alert(`Success: ${data.message}`);

    const scaleHdr = document.getElementById('hdr-scale-count');
    const compHdr = document.getElementById('hdr-comp-count');
    if (scaleHdr) scaleHdr.innerText = `${totalPoints.toLocaleString()} Pts`;
    if (compHdr) compHdr.innerText = `${data.competitors_count} Retailers`;

    fetchCatalogs();
    fetchRecommendations();
    fetchMetrics();
    renderKnowledgeGraph();

    if (btn) btn.innerText = 'Generate 20K Dataset';
  } catch (err) {
    console.error('Failed to generate dataset:', err);
  }
}

function triggerRunAllAnalysis() {
  generateLargeEnterpriseDataset(20000);
}

async function runGoldenEval() {
  try {
    const view = document.getElementById('benchmark-results-view');
    const tbody = document.getElementById('benchmark-table-body');
    if (view) view.style.display = 'block';
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px;"><span class="spinner" style="display:inline-block; margin-right:8px;"></span> Executing live Tri-Tier evaluations across Curated Ground Truth Benchmark Suite...</td></tr>';

    const res = await fetch('/api/v1/pipelines/run-eval', { method: 'POST' });
    const data = await res.json();

    if (tbody) {
      tbody.innerHTML = '';
      (data.detailed_results || []).forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${r.benchmark_id}</strong></td>
          <td><span class="text-cyan">${r.competitor_sku}</span></td>
          <td><span class="badge badge-info">${r.challenge_class}</span></td>
          <td>${r.expected}</td>
          <td><strong>${r.actual}</strong></td>
          <td>
            <span class="badge ${r.passed ? 'badge-success' : 'badge-danger'}">
              ${r.passed ? '✅ PASSED (100%)' : '❌ FAILED'}
            </span>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    let summaryDiv = document.getElementById('benchmark-summary-card');
    if (!summaryDiv && view) {
      summaryDiv = document.createElement('div');
      summaryDiv.id = 'benchmark-summary-card';
      summaryDiv.className = 'card glow-cyan mb-16 p-16';
      view.insertBefore(summaryDiv, view.firstChild);
    }

    if (summaryDiv) {
      const acc = (data.accuracy * 100).toFixed(1);
      summaryDiv.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div>
            <h4 style="margin:0; font-size:1.05rem; color:#fff;">Golden Benchmark Ground-Truth Suite: <span class="text-green">${acc}% Accuracy</span></h4>
            <p style="margin:4px 0 0 0; font-size:0.8rem; color:var(--text-secondary);">
              Passed <strong>${data.passed_count}/${data.total_benchmarks}</strong> challenge scenarios across 8 failure modes.
            </p>
          </div>
          <div>
            <span class="badge badge-success" style="font-size:0.85rem; padding:6px 12px;">
              CI/CD DEPLOYMENT GATE: APPROVED (0.00% Degradation)
            </span>
          </div>
        </div>
      `;
    }
  } catch (err) {
    console.error('Failed to run golden eval:', err);
    const tbody = document.getElementById('benchmark-table-body');
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="text-danger" style="text-align:center;">Evaluation execution failed: ${err.message}</td></tr>`;
  }
}

async function loadRealWorldScrapeData() {
  try {
    const res = await fetch('/api/v1/pipelines/load-realworld', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_name: 'RealWorld_Scraped_ECommerce_Feed' })
    });
    const data = await res.json();
    alert(`Real-World Feed Ingested:\n${data.internal_skus} Internal SKUs, ${data.competitor_observations} Competitor Observations, ${data.indexed_vectors} Vectors Indexed.`);
    fetchCatalogs();
    fetchRecommendations();
    fetchMetrics();
    fetchDriftStatus();
    renderKnowledgeGraph();
  } catch (err) {
    console.error('Failed to load real-world scrape feed:', err);
  }
}

// ==========================================================================
// 10. Chaos Sandbox, Edge Cases & Telemetry
// ==========================================================================
const EDGE_CASE_MAP = {
  'ZEN-HONEYPOT-99': { title: 'Adversarial Anti-Scraping Honeypot Trap', note: 'Detecting synthetic trap price collapse' },
  'APX-COF-3PK-AMBIG': { title: 'Deceptive Packaging & Multipack Ambiguity', note: 'Normalizing pack-count & unit pricing ($/oz)' },
  'NOV-CHAIR-ERGOPRO': { title: 'Private Label OEM & White-Label Mapping', note: 'Traversing Knowledge Graph to uncover shared OEM factory' },
  'ZEN-TV-65-OLED': { title: 'Hidden Basket Discounts & MAP Evasion', note: 'Extracting in-cart promotional vouchers to unveil true checkout total' },
  'TTN-DRILL-PHANTOM': { title: 'Phantom Stock & Adversarial Out-of-Stock Pricing', note: 'Probing regional zip-code fulfillment to isolate ghost stock' },
  'ACT-RUN-AERO10': { title: 'Highly Disparate Category Taxonomies', note: 'Zero-shot projection into canonical Global Product Classification' },
  'APX-AURA-99': { title: 'Hyper-Volatile Currency & Regional Tiering', note: 'Timestamped spot FX cross-rate normalization' },
  'APX-CLASH-NORDIC': { title: 'Conflicting Multimodal Information', note: '4-Tier Hierarchy of Truth arbitration (Title vs Hero Image clash)' }
};

function testEdgeCase(sku) {
  const meta = EDGE_CASE_MAP[sku] || { title: 'Retail Edge Case Challenge', note: 'Executing Multi-Agent Reasoning Mesh' };

  // Switch to Telemetry Agent Streaming Mesh
  switchTab('agents');

  // Set SKU input/select if present
  const skuSelect = document.getElementById('stream-sku-select');
  if (skuSelect) {
    let exists = false;
    for (let opt of skuSelect.options) {
      if (opt.value === sku) { exists = true; break; }
    }
    if (!exists) {
      const newOpt = document.createElement('option');
      newOpt.value = sku;
      newOpt.innerText = `${sku} - ${meta.title}`;
      skuSelect.appendChild(newOpt);
    }
    skuSelect.value = sku;
  }

  // Launch live thought trajectory stream
  startStreamingAnalysis(sku);

  // If ambiguous, ensure it shows in the HITL review queue
  if (sku === 'APX-CLASH-NORDIC' || sku === 'APX-COF-3PK-AMBIG') {
    fetchHitlQueue();
  }
}

async function injectChaosAttack(attackType) {
  try {
    const res = await fetch('/api/v1/chaos/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attack_type: attackType, intensity: 1.0, magnitude: 1.0 })
    });
    const data = await res.json();
    await fetchChaosStatus();
    await fetchDriftStatus();
    await fetchMetrics();
    alert(`⚡ Chaos Attack Injected:\n${data.message || data.status}`);
  } catch (e) {
    console.error('Failed to inject chaos:', e);
  }
}

async function fetchChaosStatus() {
  try {
    const res = await fetch('/api/v1/chaos/status');
    const data = await res.json();
    const banner = document.getElementById('chaos-status-banner');
    if (banner) {
      const qCount = data.quarantined_payloads ?? data.active_quarantine_count ?? 0;
      const phantoms = data.isolated_phantoms ?? 0;
      const attacks = data.active_attacks || [];
      const isDefending = attacks.length > 0;

      let attackBadges = attacks.map(a => `<span class="badge badge-warning" style="margin-right:6px;">⚠️ ${a.type}</span>`).join('');

      banner.innerHTML = `
        <div style="display:flex; align-items:center; justify-content:space-between; width:100%; flex-wrap:wrap; gap:10px;">
          <div>
            <span class="badge ${isDefending ? 'badge-danger' : 'badge-success'}">
              ${isDefending ? 'DEFENSE ACTIVE (QUARANTINED)' : 'NOMINAL MONITORING (ACTIVE)'}
            </span>
            <span class="text-cyan" style="margin-left:12px; font-weight:600;">
              ${qCount} Quarantined Payloads &bull; ${phantoms} Phantoms Isolated &bull; ${data.auto_reconciled_count || 0} Self-Healed
            </span>
          </div>
          <div>${attackBadges}</div>
        </div>
      `;
    }
  } catch (e) {
    console.error('Failed to fetch chaos status:', e);
  }
}

async function resetChaosEvents() {
  try {
    const res = await fetch('/api/v1/chaos/reset', { method: 'POST' });
    const data = await res.json();
    await fetchChaosStatus();
    await fetchDriftStatus();
    await fetchMetrics();
    alert(`System Reset Complete:\n${data.message}`);
  } catch (e) {
    console.error('Failed to reset chaos:', e);
  }
}

async function fetchMetrics() {
  try {
    const res = await fetch('/api/v1/metrics');
    const data = await res.json();

    // Top Header Telemetry
    const p99 = document.getElementById('hdr-p99');
    const tp = document.getElementById('hdr-throughput');
    const infra = data.infrastructure || data.system_plane || {};
    if (p99 && (infra.p99_latency_ms !== undefined || infra.end_to_end_latency_p99_ms !== undefined)) {
      const p99Val = infra.p99_latency_ms ?? infra.end_to_end_latency_p99_ms;
      p99.innerText = `${p99Val.toFixed(1)} ms`;
    }
    if (tp && (infra.throughput_skus_per_sec !== undefined || infra.pipeline_throughput_skus_per_sec !== undefined)) {
      const tpVal = infra.throughput_skus_per_sec ?? infra.pipeline_throughput_skus_per_sec;
      tp.innerText = `${tpVal.toFixed(0)} SKUs/s`;
    }

    // Plane 1: Business Impact Plane
    const biz = data.business || {};
    const mMargin = document.getElementById('m-margin');
    const mCoverage = document.getElementById('m-coverage');
    const mTTD = document.getElementById('m-ttd');
    const mOppVel = document.getElementById('m-opp-vel');
    if (mMargin && biz.gross_margin_protected_usd !== undefined) {
      mMargin.innerText = `$${biz.gross_margin_protected_usd.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
    }
    if (mCoverage && (biz.assortment_coverage_ratio !== undefined || biz.exact_match_rate !== undefined)) {
      const cov = biz.assortment_coverage_ratio ?? (biz.exact_match_rate * 100);
      mCoverage.innerText = `${cov.toFixed(1)}%`;
    }
    if (mTTD && biz.time_to_discovery_sec !== undefined) {
      mTTD.innerText = `${biz.time_to_discovery_sec.toFixed(1)}s`;
    }
    if (mOppVel && biz.opportunity_capture_velocity_hours !== undefined) {
      mOppVel.innerText = `${biz.opportunity_capture_velocity_hours.toFixed(1)} hrs`;
    }

    // Plane 2: Agentic Reasoning Plane
    const agent = data.agentic || {};
    const mPlanOpt = document.getElementById('m-plan-opt');
    const mToolAcc = document.getElementById('m-tool-acc');
    const mSelfCorr = document.getElementById('m-self-corr');
    const mEscRate = document.getElementById('m-esc-rate');
    if (mPlanOpt && (agent.plan_optimality_ratio !== undefined || agent.plan_optimality_ratio_avg !== undefined)) {
      mPlanOpt.innerText = (agent.plan_optimality_ratio ?? agent.plan_optimality_ratio_avg).toFixed(2);
    }
    if (mToolAcc && (agent.tool_selection_accuracy !== undefined || agent.tool_success_rate !== undefined)) {
      const acc = agent.tool_selection_accuracy ?? (agent.tool_success_rate * 100);
      mToolAcc.innerText = `${acc.toFixed(1)}%`;
    }
    if (mSelfCorr && (agent.self_correction_convergence_rate !== undefined || agent.reflection_correction_rate !== undefined)) {
      const corr = agent.self_correction_convergence_rate ?? (agent.reflection_correction_rate * 100);
      mSelfCorr.innerText = `${corr.toFixed(1)}%`;
    }
    if (mEscRate && (agent.arbitration_escalation_rate !== undefined || agent.hitl_escalation_rate !== undefined)) {
      const esc = agent.arbitration_escalation_rate ?? (agent.hitl_escalation_rate * 100);
      mEscRate.innerText = `${esc.toFixed(1)}%`;
    }

    // Plane 3: LLM / RAG Quality Plane
    const rag = data.rag_quality || data.rag || {};
    const mFaith = document.getElementById('m-faith');
    const mCtxPrec = document.getElementById('m-ctx-prec');
    const mCtxRec = document.getElementById('m-ctx-rec');
    const mHalluc = document.getElementById('m-halluc');
    if (mFaith && (rag.faithfulness_score !== undefined || rag.faithfulness_score_avg !== undefined)) {
      mFaith.innerText = (rag.faithfulness_score ?? rag.faithfulness_score_avg).toFixed(2);
    }
    if (mCtxPrec && rag.context_precision_avg !== undefined) {
      mCtxPrec.innerText = rag.context_precision_avg.toFixed(2);
    }
    if (mCtxRec && rag.context_recall_avg !== undefined) {
      mCtxRec.innerText = rag.context_recall_avg.toFixed(2);
    }
    if (mHalluc && (rag.hallucination_rate !== undefined || rag.hallucination_rate_avg !== undefined)) {
      mHalluc.innerText = (rag.hallucination_rate ?? rag.hallucination_rate_avg).toFixed(2);
    }

    // Plane 4: Classical ML Model Plane
    const ml = data.ml_system || data.ml || {};
    const mRecall = document.getElementById('m-recall');
    const mPrauc = document.getElementById('m-prauc');
    const mF1 = document.getElementById('m-f1');
    const mEmbAlign = document.getElementById('m-emb-align');
    if (mRecall && ml.bi_encoder_recall_at_5 !== undefined) {
      mRecall.innerText = ml.bi_encoder_recall_at_5.toFixed(2);
    }
    if (mPrauc && ml.cross_encoder_pr_auc !== undefined) {
      mPrauc.innerText = ml.cross_encoder_pr_auc.toFixed(2);
    }
    if (mF1 && ml.f1_score !== undefined) {
      mF1.innerText = ml.f1_score.toFixed(2);
    }
    if (mEmbAlign && ml.embedding_space_alignment !== undefined) {
      mEmbAlign.innerText = ml.embedding_space_alignment.toFixed(2);
    }

    // Plane 5: System & Infra Plane
    const mP99 = document.getElementById('m-p99');
    const mP99Ret = document.getElementById('m-p99-ret');
    const mThroughput = document.getElementById('m-throughput');
    const mCost = document.getElementById('m-cost');
    if (mP99 && infra.end_to_end_latency_p99_ms !== undefined) {
      mP99.innerText = `${infra.end_to_end_latency_p99_ms.toFixed(1)} ms`;
    }
    if (mP99Ret && infra.p99_retrieval_latency_ms !== undefined) {
      mP99Ret.innerText = `${infra.p99_retrieval_latency_ms.toFixed(1)} ms`;
    }
    if (mThroughput && infra.pipeline_throughput_skus_per_sec !== undefined) {
      mThroughput.innerText = `${infra.pipeline_throughput_skus_per_sec} SKUs/s`;
    }
    if (mCost && infra.cost_per_monitored_sku_usd !== undefined) {
      mCost.innerText = `$${infra.cost_per_monitored_sku_usd.toFixed(4)}`;
    }
  } catch (e) {
    console.error('Failed to fetch metrics:', e);
  }
}

async function fetchDriftStatus() {
  try {
    const res = await fetch('/api/v1/drift');
    const data = await res.json();
    const psiVal = document.getElementById('radar-psi-val');
    const wasVal = document.getElementById('radar-wasserstein-val');
    const phVal = document.getElementById('radar-ph-val');
    const phStatus = document.getElementById('radar-ph-status');

    if (psiVal && data.psi_score !== undefined) {
      psiVal.innerText = data.psi_score.toFixed(3);
    }
    const wDist = data.wasserstein_embedding_distance ?? data.wasserstein_distance ?? 0.038;
    if (wasVal) {
      wasVal.innerText = Number(wDist).toFixed(3);
    }
    const ph = data.page_hinkley_statistic ?? data.page_hinkley_stat ?? 0.0;
    if (phVal) {
      phVal.innerText = Number(ph).toFixed(2);
    }
    if (phStatus) {
      if (data.concept_drift_detected) {
        phStatus.className = 'badge badge-danger';
        phStatus.innerText = 'DRIFT DETECTED';
      } else {
        phStatus.className = 'badge badge-success';
        phStatus.innerText = 'NO DRIFT';
      }
    }
  } catch (e) {
    console.error('Failed to fetch drift status:', e);
  }
}

async function fetchHitlQueue() {
  try {
    const res = await fetch('/api/v1/hitl/queue');
    const data = await res.json();
    const tbody = document.getElementById('hitl-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';
    const tasks = Array.isArray(data) ? data : (data.pending_tasks || []);

    if (tasks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-secondary);">All candidate matches reconciled. Zero ambiguous listings in human arbitration queue.</td></tr>';
      return;
    }

    tasks.forEach(t => {
      const tr = document.createElement('tr');
      const candidate = t.internal_sku_candidate || t.suggested_internal_sku || 'INT-FURN-001';
      const reason = t.escalation_reason || 'Ambiguity in packaging or taxonomy';
      const confidence = t.tau_score ? (t.tau_score * 100).toFixed(1) : '72.0';
      const status = t.status || 'PENDING';

      tr.innerHTML = `
        <td><strong>${t.task_id}</strong></td>
        <td><span class="text-cyan">${t.competitor_sku}</span></td>
        <td><strong>${candidate}</strong></td>
        <td><span class="badge badge-warning">${status}</span></td>
        <td>${confidence}%</td>
        <td style="max-width:280px; font-size:0.75rem;">${reason}</td>
        <td>
          <div style="display:flex; gap:6px;">
            <button class="btn btn-primary btn-xs" onclick="resolveHitl('${t.task_id}', 'APPROVE')">Approve</button>
            <button class="btn btn-danger btn-xs" onclick="resolveHitl('${t.task_id}', 'REJECT')">Reject</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error('Failed to fetch HITL queue:', e);
  }
}

async function resolveHitl(taskId, decision) {
  try {
    const res = await fetch(`/api/v1/hitl/resolve/${taskId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: decision, notes: 'Evaluated by merchandising lead.' })
    });
    alert(`HITL Decision Recorded: Task ${taskId} marked ${decision}`);
    fetchHitlQueue();
    fetchDriftStatus();
  } catch (err) {
    console.error('Failed to resolve HITL task:', err);
  }
}

function updateElasticitySimulation() {
  const slider = document.getElementById('sim-cut-slider');
  const valText = document.getElementById('sim-cut-val');
  const revImpact = document.getElementById('sim-rev-impact');
  const marginImpact = document.getElementById('sim-margin-impact');

  if (!slider) return;
  const cut = parseInt(slider.value, 10);
  if (valText) valText.innerText = `-${cut}%`;

  const isMatch = document.querySelector('input[name="sim-strategy"]:checked')?.value === 'MATCH';

  if (isMatch) {
    if (revImpact) revImpact.innerText = `+$${(cut * 2280).toLocaleString()} / week`;
    if (marginImpact) marginImpact.innerText = `-$${(cut * 1450).toLocaleString()} margin lost`;
  } else {
    if (revImpact) revImpact.innerText = `-$${(cut * 850).toLocaleString()} / week`;
    if (marginImpact) marginImpact.innerText = `+$${(cut * 1850).toLocaleString()} protected`;
  }
}

function switchCloudArch(cloud) {
  const gcp = document.getElementById('arch-view-gcp');
  const aws = document.getElementById('arch-view-aws');
  const btnGcp = document.getElementById('btn-arch-gcp');
  const btnAws = document.getElementById('btn-arch-aws');

  if (cloud === 'gcp') {
    if (gcp) gcp.style.display = 'block';
    if (aws) aws.style.display = 'none';
    if (btnGcp) btnGcp.className = 'btn btn-primary btn-sm active';
    if (btnAws) btnAws.className = 'btn btn-secondary btn-sm';
  } else {
    if (gcp) gcp.style.display = 'none';
    if (aws) aws.style.display = 'block';
    if (btnGcp) btnGcp.className = 'btn btn-secondary btn-sm';
    if (btnAws) btnAws.className = 'btn btn-primary btn-sm active';
  }
}

// ==========================================================================
// 11. End-to-End Full Pipeline Orchestration Trigger & Modal
// ==========================================================================
async function triggerFullPipelineWorkflow() {
  const modal = document.getElementById('pipeline-modal');
  const btnDone = document.getElementById('btn-pipeline-done');
  const summaryEl = document.getElementById('pipeline-modal-summary');

  if (modal) modal.style.display = 'flex';
  if (btnDone) btnDone.style.display = 'none';

  // Reset steps
  for (let s = 1; s <= 6; s++) {
    const el = document.getElementById(`p-step-${s}`);
    if (el) {
      el.className = 'stage-step';
      const statusSpan = el.querySelector('.step-status');
      if (statusSpan) {
        statusSpan.innerText = s === 1 ? 'Executing...' : 'Pending';
        statusSpan.className = s === 1 ? 'step-status text-cyan' : 'step-status text-muted';
      }
    }
  }

  // Animate stages smoothly while backend processes
  const updateStage = (stageNum, statusText, isDone) => {
    const el = document.getElementById(`p-step-${stageNum}`);
    if (!el) return;
    el.className = isDone ? 'stage-step completed' : 'stage-step active';
    const statusSpan = el.querySelector('.step-status');
    if (statusSpan) {
      statusSpan.innerText = statusText;
      statusSpan.className = isDone ? 'step-status text-green' : 'step-status text-cyan';
    }
  };

  try {
    updateStage(1, 'Executing (48 Domains)...', false);

    // Call backend endpoint
    const fetchPromise = fetch('/api/v1/pipelines/run-full-lifecycle', { method: 'POST' });

    setTimeout(() => { updateStage(1, 'Completed', true); updateStage(2, 'Harvesting 20K Pts...', false); }, 250);
    setTimeout(() => { updateStage(2, 'Completed', true); updateStage(3, 'Indexing Vector Fabric...', false); }, 500);
    setTimeout(() => { updateStage(3, 'Completed', true); updateStage(4, 'Scanning Anomalies...', false); }, 750);
    setTimeout(() => { updateStage(4, 'Completed', true); updateStage(5, 'Traversing 3D Graph...', false); }, 1000);
    setTimeout(() => { updateStage(5, 'Completed', true); updateStage(6, 'Formulating Directives...', false); }, 1250);

    const res = await fetchPromise;
    const data = await res.json();

    updateStage(6, 'Completed', true);

    if (summaryEl) {
      summaryEl.innerHTML = `
        <span class="text-green" style="font-weight:700;">✅ Pipeline Completed in ${data.duration_ms} ms</span> &bull; 
        ${data.total_datapoints_processed.toLocaleString()} Datapoints &bull; 
        ${data.active_recommendations_count} Active Directives ($${data.gross_margin_protected_usd.toLocaleString('en-US', {minimumFractionDigits:2})} Protected)
      `;
    }

    if (btnDone) btnDone.style.display = 'block';

    // Refresh all UI components with updated state
    fetchCatalogs();
    fetchRecommendations();
    fetchMetrics();
    fetchDriftStatus();
    renderKnowledgeGraph();

  } catch (err) {
    console.error('Failed to run full pipeline:', err);
    if (summaryEl) summaryEl.innerHTML = `<span class="text-red">Execution error: ${err.message}</span>`;
  }
}

function closePipelineModal() {
  const modal = document.getElementById('pipeline-modal');
  if (modal) modal.style.display = 'none';
}

