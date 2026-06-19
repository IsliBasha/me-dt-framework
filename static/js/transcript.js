/**
 * Transcript panel — fetches /api/transcripts and renders a collapsible
 * prompt/response log for all Mythos AI calls (Mode A, B, C).
 */
const TranscriptPanel = (() => {
  let _expanded = false;
  let _intervalId = null;

  const MODE_COLORS = { A: '#4a9eff', B: '#f5a623', C: '#9b59b6' };
  const MODE_LABELS = { A: 'Mode A', B: 'Mode B', C: 'Mode C' };

  function _truncate(str, n) {
    if (str == null) return '—';
    str = String(str);
    return str.length > n ? str.slice(0, n) + '…' : str;
  }

  function _modeBadge(mode) {
    const color = MODE_COLORS[mode] || '#666';
    const label = MODE_LABELS[mode] || mode;
    return `<span class="tx-mode-badge" style="background:${color}">${label}</span>`;
  }

  function _responseSummary(entry) {
    const p = entry.parsed_result;
    if (!p) return `<span class="tx-err">${_truncate(entry.response_raw, 50)}</span>`;
    if (entry.mode === 'A' && p.threat_class) {
      const pct = ((p.confidence || 0) * 100).toFixed(0);
      return `<span class="threat-class-badge badge-${p.threat_class}">${p.threat_class}</span>`
           + `<span class="tx-conf">${pct}%</span>`;
    }
    if (entry.mode === 'B' && p.entry_point) {
      return `<span class="tx-ep">${_truncate(p.entry_point, 36)}</span>`;
    }
    if (entry.mode === 'C' && Array.isArray(p) && p[0]) {
      return `<span class="tx-hyp">${_truncate(p[0].attack_class, 36)}</span>`;
    }
    return _truncate(JSON.stringify(p), 60);
  }

  function _renderEntry(entry) {
    const promptText = _truncate(entry.prompt, 450);
    const rawText    = _truncate(entry.response_raw, 450);
    return `
      <details class="tx-entry">
        <summary class="tx-summary">
          <span class="tx-tick">T${String(entry.tick).padStart(4, '0')}</span>
          ${_modeBadge(entry.mode)}
          <span class="tx-result">${_responseSummary(entry)}</span>
          <span class="tx-lat">${entry.latency_ms.toFixed(0)}ms</span>
        </summary>
        <div class="tx-body">
          <div class="tx-col">
            <div class="tx-col-label">PROMPT</div>
            <div class="tx-col-content">${promptText}</div>
          </div>
          <div class="tx-col">
            <div class="tx-col-label">RESPONSE</div>
            <div class="tx-col-content">${rawText}</div>
          </div>
        </div>
      </details>`;
  }

  async function refresh() {
    const container = document.getElementById('tx-list');
    if (!container) return;
    try {
      const res = await fetch('/api/transcripts?n=15');
      if (!res.ok) return;
      const data = await res.json();
      const entries = [...data].reverse();
      container.innerHTML = entries.length
        ? entries.map(_renderEntry).join('')
        : '<div class="tx-empty">No AI calls recorded yet — start the simulation</div>';
    } catch (_) {}
  }

  function toggle() {
    const body = document.getElementById('tx-panel-body');
    const btn  = document.getElementById('tx-toggle-btn');
    if (!body || !btn) return;
    _expanded = !_expanded;
    body.style.display = _expanded ? 'block' : 'none';
    btn.textContent = _expanded ? '▲' : '▼';
    if (_expanded) {
      refresh();
      _intervalId = setInterval(refresh, 8000);
    } else {
      clearInterval(_intervalId);
      _intervalId = null;
    }
  }

  function init() {
    const toggleBtn  = document.getElementById('tx-toggle-btn');
    const refreshBtn = document.getElementById('tx-refresh-btn');
    if (toggleBtn)  toggleBtn.addEventListener('click', toggle);
    if (refreshBtn) refreshBtn.addEventListener('click', () => { if (_expanded) refresh(); });
  }

  return { init, refresh };
})();

document.addEventListener('DOMContentLoaded', () => TranscriptPanel.init());
