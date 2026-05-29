/**
 * dashboard.js — WebSocket client + state manager + attack control panel
 */

const Dashboard = (() => {
  let ws = null;
  let reconnectTimer = null;
  let currentTick = 0;
  let currentSpeed = 1.0;
  let activeAttack = null;
  let attackPanelOpen = false;
  const _seenEventIds = new Set();
  const _violationLastShown = {};   // rule_id -> tick last shown
  const VIOLATION_COOLDOWN = 30;    // suppress repeat violations for this many ticks

  const WS_URL = `ws://${location.host}/ws`;

  // -----------------------------------------------------------------------
  // WebSocket
  // -----------------------------------------------------------------------
  function connect() {
    ws = new WebSocket(WS_URL);
    ws.onopen    = () => { _setConnStatus('CONNECTED', '#10b981'); };
    ws.onclose   = () => { _setConnStatus('DISCONNECTED', '#ef4444'); _scheduleReconnect(); };
    ws.onerror   = () => { _setConnStatus('ERROR', '#ef4444'); };
    ws.onmessage = (e) => {
      try { _handlePayload(JSON.parse(e.data)); }
      catch (err) { console.error('[WS] Parse error', err); }
    };
  }

  function _scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => { reconnectTimer = null; connect(); }, 3000);
  }

  // -----------------------------------------------------------------------
  // Payload handler
  // -----------------------------------------------------------------------
  function _handlePayload(p) {
    currentTick  = p.tick ?? currentTick;
    activeAttack = p.active_attack ?? null;

    // Header
    _setText('hdr-tick',   currentTick);
    _setText('hdr-speed',  `${currentSpeed}x`);
    const badge = document.getElementById('hdr-threat');
    if (badge) {
      badge.className = `threat-badge ${p.threat_level || 'NONE'}`;
      badge.textContent = p.threat_level || 'NONE';
    }

    // CRITICAL card glow
    document.querySelectorAll('.card').forEach(c => {
      c.classList.toggle('threat-critical', p.threat_level === 'CRITICAL');
    });

    // City map
    if (p.twin_state) CityMap.update(p.twin_state);

    // Charts
    Charts.update(p);

    // AI panel
    if (p.mode_a)  ThreatFeed.updateModeA(p.mode_a);
    if (p.mode_b)  ThreatFeed.updateModeB(p.mode_b);
    const modeCAct = Array.isArray(p.mode_c) && p.mode_c.length > 0;
    ThreatFeed.updateModeC(p.mode_c, modeCAct);

    // Event feed — deduplicate by alert_id so each event appears only once
    const newEvents = (p.event_log || []).filter(e => {
      if (!e.alert_id || _seenEventIds.has(e.alert_id)) return false;
      _seenEventIds.add(e.alert_id);
      return true;
    });
    const newViolations = (p.violations || []).filter(v => {
      const key = v.rule_id + '_' + (v.affected_nodes || []).slice().sort().join(',');
      const last = _violationLastShown[key];
      if (last !== undefined && currentTick - last < VIOLATION_COOLDOWN) return false;
      _violationLastShown[key] = currentTick;
      return true;
    });
    ThreatFeed.addEvents(newEvents, newViolations);

    // Baseline table
    ThreatFeed.updateBaseline(p.metrics);

    // Vulnerability atlas
    ThreatFeed.updateAtlas(p.vulnerability_atlas);

    // Metrics gauges
    _updateMetrics(p.metrics, p.mode_a);

    // Attack panel active indicator
    const banner = document.getElementById('active-attack-banner');
    if (banner) {
      if (activeAttack) {
        banner.textContent = `ACTIVE: ${activeAttack.toUpperCase()}`;
        banner.classList.add('visible');
      } else {
        banner.classList.remove('visible');
      }
    }

    // Attack propagation animation
    if (p.mode_b?.entry_point && p.mode_b?.attack_steps?.length) {
      const affectedNodes = p.mode_b.attack_steps.map(s => s.target_node).filter(Boolean);
      CityMap.animateAttack(p.mode_b.entry_point.split('/')[0], affectedNodes);
    }
  }

  // -----------------------------------------------------------------------
  // Metrics gauges
  // -----------------------------------------------------------------------
  function _updateMetrics(metrics, modeA) {
    if (!metrics) return;
    const medt = metrics.me_dt || {};
    const latency = medt.mean_latency_ms || (modeA?.api_latency_ms) || 0;
    const tpRate  = medt.tp_count ? (medt.tp_count / (medt.tp_count + (medt.fp_count||0)) * 100).toFixed(0) : '—';
    const fpRate  = medt.fp_count ? medt.fp_count.toString() : '0';

    _setText('metric-latency', latency ? latency.toFixed(0) + ' ms' : '—');
    _setText('metric-tp',      tpRate !== '—' ? tpRate + '%' : '—');
    _setText('metric-fp',      fpRate);
    _setText('metric-alerts',  medt.tp_count ?? 0);

    // Baseline row counts
    _setText('bl-cusum-alerts',     metrics.cusum?.alerts_count ?? 0);
    _setText('bl-isoforest-alerts', metrics.isoforest?.alerts_count ?? 0);
    _setText('bl-medt-alerts',      medt.tp_count ?? 0);
    _setText('bl-cusum-fp',     metrics.cusum?.fp_count ?? 0);
    _setText('bl-isoforest-fp', metrics.isoforest?.fp_count ?? 0);
    _setText('bl-medt-fp',      medt.fp_count ?? 0);
  }

  // -----------------------------------------------------------------------
  // Attack control panel
  // -----------------------------------------------------------------------
  const ATTACKS = [
    { name:'false_data_injection',       label:'FALSE DATA INJECTION', severity:'HIGH',     sim:'WNTR' },
    { name:'water_hammer',               label:'WATER HAMMER',         severity:'HIGH',     sim:'WNTR' },
    { name:'load_redistribution',        label:'LOAD REDISTRIBUTION',  severity:'CRITICAL', sim:'pandapower' },
    { name:'false_data_injection_power', label:'FDI POWER (BDD)',       severity:'HIGH',     sim:'pandapower' },
    { name:'scada_replay',               label:'SCADA REPLAY',         severity:'HIGH',     sim:'pandapower' },
    { name:'cross_domain_cascade',       label:'CROSS-DOMAIN CASCADE', severity:'CRITICAL', sim:'pandapower' },
    { name:'actuator_hijack',            label:'ACTUATOR HIJACK',      severity:'CRITICAL', sim:'WNTR' },
    { name:'low_and_slow_recon',         label:'LOW-AND-SLOW RECON',   severity:'MEDIUM',   sim:'WNTR' },
    { name:'denial_of_service_ot',       label:'DENIAL OF SERVICE OT', severity:'HIGH',     sim:'LAYER2' },
  ];

  function _buildAttackPanel() {
    const btnsEl = document.getElementById('attack-buttons');
    if (!btnsEl) return;
    btnsEl.innerHTML = ATTACKS.map(a => `
      <button class="attack-btn" onclick="Dashboard.injectAttack('${a.name}')">
        <span>${a.label}</span>
        <span class="attack-btn-badges">
          <span class="attack-sev sev-${a.severity}">${a.severity}</span>
          <span class="sim-tag">${a.sim}</span>
        </span>
      </button>
    `).join('');
  }

  function toggleAttackPanel() {
    attackPanelOpen = !attackPanelOpen;
    const panel = document.getElementById('attack-panel');
    if (panel) panel.classList.toggle('open', attackPanelOpen);
  }

  async function injectAttack(scenario, delay=0) {
    try {
      const resp = await fetch('/api/inject-attack', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario, delay }),
      });
      const data = await resp.json();
      console.log('[Attack]', data);
    } catch (e) {
      console.error('[Attack inject error]', e);
    }
  }

  async function setSpeed(multiplier) {
    currentSpeed = multiplier;
    _setText('hdr-speed', `${multiplier}x`);
    document.querySelectorAll('.speed-btn').forEach(b => {
      b.classList.toggle('active', parseFloat(b.dataset.speed) === multiplier);
    });
    await fetch('/api/speed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ multiplier }),
    });
  }

  async function resetSim() {
    await fetch('/api/reset', { method: 'POST' });
    console.log('[Dashboard] Simulation reset');
  }

  // -----------------------------------------------------------------------
  // Approval Queue
  // -----------------------------------------------------------------------
  const _resolvedActionIds = new Set();

  function _renderQueueItem(action) {
    const pct = Math.round(action.confidence * 100);
    return `
      <div class="queue-item" id="qitem-${action.action_id}">
        <div class="queue-item-info">
          <div class="queue-item-meta">
            <span class="queue-threat-class">${action.threat_class || 'UNKNOWN'}</span>
            <span class="queue-node">${action.node_id}</span>
            <span class="queue-subsystem">${action.subsystem}</span>
          </div>
          <div class="queue-conf-row">
            <span class="queue-conf-label">Confidence</span>
            <div class="queue-conf-bar"><div class="queue-conf-fill" style="width:${pct}%"></div></div>
            <span class="queue-conf-pct">${pct}%</span>
          </div>
          <div class="queue-evidence">${action.evidence_trace || '&mdash;'}</div>
          <div class="queue-response">&#x27A4; ${action.recommended_response || '&mdash;'}</div>
          <div class="queue-tick">Queued at T${action.tick}</div>
        </div>
        <div class="queue-btns">
          <button class="queue-approve-btn" onclick="Dashboard.approveAction('${action.action_id}')">&#x2713; Approve</button>
          <button class="queue-reject-btn"  onclick="Dashboard.rejectAction('${action.action_id}')">&#x2715; Reject</button>
        </div>
      </div>`;
  }

  function _makeEmpty() {
    const d = document.createElement('div');
    d.id = 'queue-empty';
    d.className = 'queue-empty';
    d.textContent = 'No pending actions — system operating within auto-contain bounds';
    return d;
  }

  function _updateApprovalQueue(pending) {
    const list  = document.getElementById('approval-list');
    const badge = document.getElementById('queue-badge');
    if (!list) return;

    const fresh = pending.filter(a => !_resolvedActionIds.has(a.action_id));

    if (fresh.length === 0) {
      const hasItems = list.querySelector('.queue-item');
      if (hasItems) {
        list.innerHTML = '';
        list.appendChild(_makeEmpty());
      }
      if (badge) badge.style.display = 'none';
      return;
    }

    if (badge) {
      badge.style.display = '';
      badge.textContent = `${fresh.length} pending`;
    }

    const existingIds = new Set(
      [...list.querySelectorAll('.queue-item')].map(el => el.id.replace('qitem-', ''))
    );
    const incomingIds = new Set(fresh.map(a => a.action_id));

    existingIds.forEach(id => {
      if (!incomingIds.has(id)) {
        const el = document.getElementById(`qitem-${id}`);
        if (el) el.remove();
      }
    });

    const emptyEl = list.querySelector('.queue-empty');
    if (emptyEl) emptyEl.remove();

    fresh.forEach(action => {
      if (!existingIds.has(action.action_id)) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = _renderQueueItem(action).trim();
        list.appendChild(wrapper.firstChild);
      }
    });
  }

  async function _pollApprovalQueue() {
    try {
      const resp = await fetch('/api/approval-queue');
      if (!resp.ok) return;
      const data = await resp.json();
      _updateApprovalQueue(data.pending || []);
    } catch (_) { /* server may be starting */ }
  }

  async function approveAction(actionId) {
    const el = document.getElementById(`qitem-${actionId}`);
    if (el) el.style.opacity = '0.4';
    try {
      await fetch('/api/approve-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, approved_by: 'operator' }),
      });
      _resolvedActionIds.add(actionId);
      if (el) el.remove();
      _pollApprovalQueue();
    } catch (_) {
      if (el) el.style.opacity = '1';
    }
  }

  async function rejectAction(actionId) {
    const el = document.getElementById(`qitem-${actionId}`);
    if (el) el.style.opacity = '0.4';
    try {
      await fetch('/api/reject-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, rejected_by: 'operator' }),
      });
      _resolvedActionIds.add(actionId);
      if (el) el.remove();
      _pollApprovalQueue();
    } catch (_) {
      if (el) el.style.opacity = '1';
    }
  }

  // -----------------------------------------------------------------------
  // Keyboard shortcuts
  // -----------------------------------------------------------------------
  function _initKeyboard() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'a' || e.key === 'A') toggleAttackPanel();
    });
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
  function _setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function _setConnStatus(status, color) {
    const el = document.getElementById('conn-status');
    if (el) { el.textContent = status; el.style.color = color; }
  }

  // -----------------------------------------------------------------------
  // Init
  // -----------------------------------------------------------------------
  function init() {
    ThreatFeed.initSections();
    CityMap.init('map-container');
    Charts.init();
    _buildAttackPanel();
    _initKeyboard();
    connect();
    _pollApprovalQueue();
    setInterval(_pollApprovalQueue, 3000);
  }

  return { init, injectAttack, setSpeed, resetSim, toggleAttackPanel, approveAction, rejectAction };
})();

window.addEventListener('DOMContentLoaded', () => Dashboard.init());
