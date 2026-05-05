/**
 * threat_feed.js — AI Reasoning Panel renderer + Threat Event Feed
 * Handles Mode A, B, C displays and the scrolling event log.
 */

const ThreatFeed = (() => {
  let _typewriterTimeout = null;

  // -----------------------------------------------------------------------
  // Collapsible AI sections
  // -----------------------------------------------------------------------
  function initSections() {
    document.querySelectorAll('.ai-section-header').forEach(header => {
      header.addEventListener('click', () => {
        const section = header.closest('.ai-section');
        section.classList.toggle('open');
        header.querySelector('.ai-section-chevron').textContent =
          section.classList.contains('open') ? '▲' : '▼';
      });
    });
    // Open Mode A by default
    document.querySelector('#ai-mode-a')?.classList.add('open');
  }

  // -----------------------------------------------------------------------
  // Mode A
  // -----------------------------------------------------------------------
  function updateModeA(modeA) {
    if (!modeA) return;

    // Threat class badge
    const badgeEl = document.getElementById('ma-threat-class');
    if (badgeEl) {
      const levelMap = { NONE:'NONE', RECONNAISSANCE:'LOW', SIGNAL_MANIPULATION:'MEDIUM',
        LOAD_REDISTRIBUTION:'HIGH', WATER_HAMMER:'HIGH', FALSE_DATA_INJECTION:'HIGH',
        SCADA_REPLAY:'HIGH', DENIAL_OF_SERVICE_OT:'HIGH', CROSS_DOMAIN_CASCADE:'CRITICAL',
        ACTUATOR_HIJACK:'CRITICAL', UNKNOWN:'MEDIUM' };
      const level = levelMap[modeA.threat_class] || 'MEDIUM';
      badgeEl.className = `threat-class-badge badge-${level}`;
      badgeEl.textContent = modeA.threat_class || 'NONE';
    }

    // Confidence bar
    const fill = document.getElementById('ma-confidence-fill');
    const pct  = Math.round((modeA.confidence || 0) * 100);
    if (fill) {
      fill.style.width = pct + '%';
      if (pct >= 90) fill.style.background = '#ef4444';
      else if (pct >= 75) fill.style.background = '#f59e0b';
      else if (pct >= 50) fill.style.background = '#00d4ff';
      else fill.style.background = '#10b981';
    }
    const pctEl = document.getElementById('ma-confidence-pct');
    if (pctEl) pctEl.textContent = pct + '%';

    // Evidence (typewriter)
    _typewriter('ma-evidence', modeA.evidence_trace || '—');

    // Physical consequence
    _setText('ma-consequence', modeA.physical_consequence || '—');

    // Response
    _setText('ma-response', modeA.recommended_response || '—');

    // Reasoning
    _setText('ma-reasoning', modeA.reasoning_chain || '—');

    // Subsystems
    const subsEl = document.getElementById('ma-subsystems');
    if (subsEl) {
      subsEl.innerHTML = (modeA.affected_subsystems || []).map(s =>
        `<span class="subsystem-pill">${s}</span>`
      ).join('') || '<span class="subsystem-pill" style="background:rgba(16,185,129,0.1);color:#10b981">NONE</span>';
    }

    // Latency
    const latEl = document.getElementById('ma-latency');
    if (latEl) {
      latEl.textContent = modeA.api_latency_ms ? `${modeA.api_latency_ms.toFixed(0)}ms` : '—';
    }
  }

  // -----------------------------------------------------------------------
  // Mode B
  // -----------------------------------------------------------------------
  function updateModeB(modeB) {
    if (!modeB) return;

    _setText('mb-last-probe', modeB.tick !== undefined ? `Tick ${modeB.tick}` : '—');
    _setText('mb-entry-point', modeB.entry_point || '—');

    const stepsEl = document.getElementById('mb-steps');
    if (stepsEl && modeB.attack_steps) {
      stepsEl.innerHTML = modeB.attack_steps.map(s => `
        <div class="step-item">
          <div class="step-num">${_escapeHtml(String(s.step))}</div>
          <div class="step-content">
            <div>${_escapeHtml(s.action)}</div>
            <div class="step-target">→ ${_escapeHtml(s.target_node)}: ${_escapeHtml(s.expected_effect)}</div>
          </div>
        </div>
      `).join('');
    }

    _setText('mb-consequence', modeB.physical_consequence || '—');
    _setText('mb-evasion', modeB.evasion_rationale || '—');

    // Impact gauge
    const gaugeEl = document.getElementById('mb-impact-gauge');
    const sev     = modeB.estimated_impact_severity || 0;
    if (gaugeEl) {
      gaugeEl.innerHTML = Array.from({length:10}, (_, i) =>
        `<div class="impact-block${i < sev ? ' filled' : ''}"></div>`
      ).join('');
    }

    // Detection difficulty
    const diffEl = document.getElementById('mb-difficulty');
    if (diffEl) {
      const diff = modeB.detection_difficulty || 'LOW';
      diffEl.className = `difficulty-badge diff-${diff}`;
      diffEl.textContent = diff;
    }
  }

  // -----------------------------------------------------------------------
  // Mode C
  // -----------------------------------------------------------------------
  function updateModeC(modeC, visible) {
    const section = document.getElementById('ai-mode-c');
    if (section) {
      section.classList.toggle('mode-c-active', visible);
      section.style.display = visible ? '' : 'none';
    }
    if (!modeC || !visible) return;

    const container = document.getElementById('mc-hypotheses');
    if (!container) return;
    container.innerHTML = (modeC || []).map(h => `
      <div class="zdh-card">
        <div class="zdh-card-header">
          <div class="zdh-rank">RANK ${_escapeHtml(String(h.rank))}</div>
          <div class="threat-class-badge badge-HIGH">${_escapeHtml(h.attack_class)}</div>
          <div class="metric-sub">Impact: ${_escapeHtml(String(h.physical_impact_severity))}/10</div>
        </div>
        <div class="ai-label">Intent</div>
        <div class="ai-value" style="font-size:10px;margin-bottom:4px">${_escapeHtml(h.attacker_intent)}</div>
        <div class="ai-label">Why IDS Misses</div>
        <div class="ai-value" style="font-size:10px;font-style:italic;margin-bottom:4px">${_escapeHtml(h.why_standard_ids_misses)}</div>
        <div class="ai-label">Recommended Monitoring</div>
        <div class="ai-value" style="font-size:10px">${_escapeHtml(h.recommended_monitoring)}</div>
      </div>
    `).join('');
  }

  // -----------------------------------------------------------------------
  // Event feed
  // -----------------------------------------------------------------------
  const _feedBuffer = [];
  const MAX_FEED = 100;

  function addEvents(events, violations) {
    for (const ev of (events || [])) {
      _feedBuffer.unshift({
        time: `T${String(ev.tick).padStart(4,'0')}`,
        source: ev.source || 'SYSTEM',
        message: ev.message || '',
        severity: ev.severity || 'LOW',
      });
    }
    for (const v of (violations || [])) {
      _feedBuffer.unshift({
        time: `T${String(v.tick).padStart(4,'0')}`,
        source: 'PHYSICS',
        message: `[${v.rule_id}] ${v.description}${v.traffic_model ? ' (' + v.traffic_model + ')' : ''}`,
        severity: v.severity || 'LOW',
      });
    }
    while (_feedBuffer.length > MAX_FEED) _feedBuffer.pop();

    const feedEl = document.getElementById('event-feed');
    if (!feedEl) return;
    feedEl.innerHTML = _feedBuffer.slice(0, 50).map(ev => `
      <div class="event-item">
        <div class="event-time">${ev.time}</div>
        <div class="event-source src-${ev.source}">${ev.source}</div>
        <div class="event-msg">${_escapeHtml(ev.message)}</div>
      </div>
    `).join('');
  }

  // -----------------------------------------------------------------------
  // Baseline comparison table
  // -----------------------------------------------------------------------
  function updateBaseline(metrics) {
    if (!metrics) return;
    const rows = [
      { name:'CUSUM',    data: metrics.cusum,     source:'CUSUM' },
      { name:'IsoForest',data: metrics.isoforest, source:'ISOFOREST' },
      { name:'ME-DT',    data: metrics.me_dt,     source:'ME-DT' },
    ];
    rows.forEach(row => {
      const d = row.data || {};
      _setText(`bl-${row.source.toLowerCase().replace('-','').replace('forest','forest')}-alerts`,
        d.alerts_count ?? d.tp_count ?? 0);
      const fpRate = d.fp_count != null && (d.alerts_count || d.tp_count)
        ? ((d.fp_count / ((d.alerts_count || d.tp_count) + d.fp_count)) * 100).toFixed(1) + '%'
        : '0.0%';
      _setText(`bl-${row.source.toLowerCase().replace('-','').replace('forest','forest')}-fp`, fpRate);
    });
  }

  // -----------------------------------------------------------------------
  // Vulnerability atlas
  // -----------------------------------------------------------------------
  function updateAtlas(atlas) {
    const tbl = document.getElementById('atlas-body');
    if (!tbl) return;
    tbl.innerHTML = (atlas || []).slice(-8).reverse().map(a => `
      <tr>
        <td>${_escapeHtml(a.entry_point || '—')}</td>
        <td><span class="difficulty-badge diff-${a.detection_difficulty||'LOW'}">${a.detection_difficulty||'—'}</span></td>
        <td>${a.estimated_impact_severity ?? '—'}/10</td>
        <td style="font-size:9px;color:#94a3b8;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${_escapeHtml(a.evasion_rationale||'—')}</td>
      </tr>
    `).join('');
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
  function _setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function _typewriter(id, text) {
    const el = document.getElementById(id);
    if (!el || el._lastText === text) return;
    el._lastText = text;
    el.textContent = '';
    let i = 0;
    if (_typewriterTimeout) clearTimeout(_typewriterTimeout);
    function tick() {
      if (i < text.length) {
        el.textContent += text[i++];
        _typewriterTimeout = setTimeout(tick, 18);
      }
    }
    tick();
  }

  function _escapeHtml(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;');
  }

  return {
    initSections,
    updateModeA,
    updateModeB,
    updateModeC,
    addEvents,
    updateBaseline,
    updateAtlas,
  };
})();
