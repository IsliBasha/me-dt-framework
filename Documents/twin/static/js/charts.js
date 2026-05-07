/**
 * charts.js — Stable real-time Chart.js sensor graphs
 *
 * Key design decisions:
 *  - {x, y} point format with type:'linear' x-axis (reliable in Chart.js 4)
 *  - animations + transitions both set to false — no implicit interpolation
 *  - vertical lines stored per-chart in a module map, not on chart.options
 *  - horizontal reference lines rendered in the same canvas plugin
 *  - anomaly markers as a separate scatter dataset (no pointBackgroundColor sync)
 */

const Charts = (() => {
  const MAX_POINTS = 60;

  let waterChart   = null;
  let powerChart   = null;
  let trafficChart = null;

  // Per-chart vertical line history: chartId -> [{tick, color, label, dash}]
  const _vlines = { water: [], power: [], traffic: [] };

  const C = {
    cyan:   '#5a8fba',  // steel blue — water primary
    amber:  '#d4923a',  // warm amber — power / CUSUM
    red:    '#d93d30',  // HAL alert red
    green:  '#2d9e72',  // muted ok green
    purple: '#c07820',  // dim amber — IsoForest
    gray:   '#4a4843',  // warm gray — traffic
    dim:    'rgba(255,255,255,0.03)',
  };

  const WATER_NODES   = ['10', '15', '20', '35'];
  const POWER_NODES   = ['0', '12', '32'];
  const TRAFFIC_NODES = ['SYN-T01', 'SYN-T02', 'SYN-T03'];

  const WATER_COLORS   = ['#5a8fba', '#4a7a9b', '#3d6685', '#305270'];
  const POWER_COLORS   = ['#d4923a', '#bf7a28', '#e0a845'];
  const TRAFFIC_COLORS = ['#5a5550', '#4a4845', '#6a6460'];

  // -----------------------------------------------------------------------
  // Canvas plugin: horizontal ref lines + vertical event lines
  // -----------------------------------------------------------------------
  const LinesPlugin = {
    id: 'linesPlugin',
    afterDraw(chart) {
      const ctx    = chart.ctx;
      const xScale = chart.scales.x;
      const yScale = chart.scales.y;
      if (!xScale || !yScale) return;

      ctx.save();

      // Horizontal reference lines (defined per-chart via chart._hlines)
      for (const hl of (chart._hlines || [])) {
        const y = yScale.getPixelForValue(hl.value);
        ctx.beginPath();
        ctx.moveTo(xScale.left, y);
        ctx.lineTo(xScale.right, y);
        ctx.strokeStyle = hl.color;
        ctx.lineWidth   = 1;
        ctx.setLineDash([4, 3]);
        ctx.globalAlpha = 0.55;
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      }

      // Vertical event lines (stored in module-level _vlines map)
      const vkey = chart._vlineKey;
      if (vkey) {
        for (const vl of (_vlines[vkey] || [])) {
          const x = xScale.getPixelForValue(vl.tick);
          if (x < xScale.left || x > xScale.right) continue;
          ctx.beginPath();
          ctx.moveTo(x, yScale.top);
          ctx.lineTo(x, yScale.bottom);
          ctx.strokeStyle = vl.color;
          ctx.lineWidth   = vl.dash?.length ? 1 : 1.5;
          ctx.setLineDash(vl.dash || []);
          ctx.globalAlpha = 0.75;
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.globalAlpha = 1;
          if (vl.label) {
            ctx.fillStyle  = vl.color;
            ctx.font       = '9px JetBrains Mono, monospace';
            ctx.globalAlpha = 0.9;
            ctx.fillText(vl.label, x + 2, yScale.top + 10);
            ctx.globalAlpha = 1;
          }
        }
      }

      ctx.restore();
    },
  };

  if (typeof Chart !== 'undefined') {
    Chart.register(LinesPlugin);
  }

  // -----------------------------------------------------------------------
  // Dataset factories
  // -----------------------------------------------------------------------
  function _lineDs(label, color) {
    return {
      type: 'line',
      label,
      data: [],                    // [{x, y}, ...]
      borderColor: color,
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      pointRadius: 0,
      pointHoverRadius: 3,
      tension: 0.25,
      spanGaps: true,
    };
  }

  function _anomalyDs() {
    return {
      type: 'scatter',
      label: '_anomaly',
      data: [],                    // [{x, y}, ...]
      borderColor: C.red,
      backgroundColor: C.red,
      pointRadius: 3,
      pointHoverRadius: 4,
      showLine: false,
    };
  }

  // -----------------------------------------------------------------------
  // Base chart options — animations fully disabled
  // -----------------------------------------------------------------------
  function _opts(yMin, yMax, unit) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      // Disable all animations/transitions
      animation: false,
      animations: { colors: false, x: false, y: false },
      transitions: { active: { animation: { duration: 0 } } },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          filter: item => item.dataset.label !== '_anomaly',
          backgroundColor: 'rgba(12,9,10,0.97)',
          borderColor: 'rgba(192,51,48,0.25)',
          borderWidth: 1,
          titleColor: C.cyan,
          bodyColor: '#d8d2cc',
          titleFont: { family: 'JetBrains Mono, monospace', size: 10 },
          bodyFont:  { family: 'JetBrains Mono, monospace', size: 10 },
          callbacks: {
            label: ctx => {
              if (ctx.dataset.label === '_anomaly') return null;
              const v = ctx.parsed?.y ?? ctx.raw?.y;
              return v != null ? `${ctx.dataset.label}: ${Number(v).toFixed(3)} ${unit}` : null;
            },
          },
        },
      },
      scales: {
        x: {
          type: 'linear',
          min: 0,
          ticks: {
            color: '#4a4540',
            font: { family: 'JetBrains Mono, monospace', size: 8 },
            maxTicksLimit: 6,
            callback: v => `T${v}`,
          },
          grid: { color: C.dim },
          border: { color: 'rgba(255,255,255,0.08)' },
        },
        y: {
          min: yMin,
          max: yMax,
          ticks: {
            color: '#4a4540',
            font: { family: 'JetBrains Mono, monospace', size: 8 },
            maxTicksLimit: 4,
          },
          grid: { color: C.dim },
          border: { color: 'rgba(255,255,255,0.08)' },
        },
      },
    };
  }

  // -----------------------------------------------------------------------
  // Init
  // -----------------------------------------------------------------------
  function init() {
    if (typeof Chart === 'undefined') {
      console.error('[Charts] Chart.js not loaded');
      return;
    }

    // Water Pressure
    const wCtx = document.getElementById('chart-water')?.getContext('2d');
    if (wCtx) {
      waterChart = new Chart(wCtx, {
        type: 'line',
        data: {
          datasets: [
            ...WATER_NODES.map((n, i) => _lineDs(n, WATER_COLORS[i])),
            _anomalyDs(),
          ],
        },
        options: (() => {
          const o = _opts(null, null, 'm');
          delete o.scales.y.min;
          delete o.scales.y.max;
          return o;
        })(),
      });
      waterChart._vlineKey = 'water';
      waterChart._hlines   = [];
    }

    // Power Voltage
    const pCtx = document.getElementById('chart-power')?.getContext('2d');
    if (pCtx) {
      powerChart = new Chart(pCtx, {
        type: 'line',
        data: {
          datasets: [
            ...POWER_NODES.map((n, i) => _lineDs(`Bus ${n}`, POWER_COLORS[i])),
            _anomalyDs(),
          ],
        },
        options: _opts(0.85, 1.08, 'pu'),
      });
      powerChart._vlineKey = 'power';
      // Reference lines at 0.90 and 1.10 drawn by plugin
      powerChart._hlines = [
        { value: 0.90, color: C.red },
        { value: 1.10, color: C.red },
      ];
    }

    // Traffic Flow (SYNTHETIC)
    const tCtx = document.getElementById('chart-traffic')?.getContext('2d');
    if (tCtx) {
      trafficChart = new Chart(tCtx, {
        type: 'line',
        data: {
          datasets: TRAFFIC_NODES.map((n, i) => _lineDs(n, TRAFFIC_COLORS[i])),
        },
        options: _opts(0, 300, 'veh/min'),
      });
      trafficChart._vlineKey = 'traffic';
      trafficChart._hlines   = [];
    }
  }

  // -----------------------------------------------------------------------
  // Data helpers
  // -----------------------------------------------------------------------
  function _push(chart, lineCount, tick, yValues, anomalyYValues = []) {
    if (!chart) return;

    // Roll window on line datasets
    for (let i = 0; i < lineCount; i++) {
      const ds = chart.data.datasets[i];
      ds.data.push({ x: tick, y: yValues[i] ?? null });
      if (ds.data.length > MAX_POINTS) ds.data.shift();
    }

    // Anomaly scatter dataset (last dataset, only if present)
    const anomDs = chart.data.datasets[lineCount];
    if (anomDs) {
      // Remove stale anomaly points outside the visible window
      const oldest = tick - MAX_POINTS;
      anomDs.data = anomDs.data.filter(p => p.x > oldest);
      anomalyYValues.forEach((y, i) => {
        if (y != null) anomDs.data.push({ x: tick, y });
      });
    }

    // Slide x-axis window
    const xScale = chart.options.scales.x;
    if (tick > MAX_POINTS) {
      xScale.min = tick - MAX_POINTS;
      xScale.max = tick;
    } else {
      xScale.min = 0;
      xScale.max = MAX_POINTS;
    }

    chart.update();
  }

  function _addVLine(key, tick, color, label, dash = [3, 2]) {
    const arr = _vlines[key];
    if (!arr) return;
    arr.push({ tick, color, label, dash });
    // Keep only points in the last MAX_POINTS window
    const oldest = tick - MAX_POINTS;
    while (arr.length && arr[0].tick < oldest) arr.shift();
  }

  // -----------------------------------------------------------------------
  // Public update — called every WebSocket tick
  // -----------------------------------------------------------------------
  function update(payload) {
    const tick    = payload.tick;
    const water   = payload.twin_state?.water   || {};
    const power   = payload.twin_state?.power   || {};
    const traffic = payload.twin_state?.traffic || {};

    // --- Water ---
    const wVals = WATER_NODES.map(n => {
      const nd = water[n];
      return nd ? (nd.value ?? nd.pressure ?? null) : null;
    });
    const wAnom = WATER_NODES.flatMap((n, i) => {
      const nd = water[n];
      if (!nd) return [];
      const isAnom = nd.status === 'SUSPECT' || nd.status === 'UNDER_ATTACK';
      return isAnom ? [{ x: tick, y: wVals[i] }] : [];
    });
    _push(waterChart, WATER_NODES.length, tick, wVals);
    if (wAnom.length && waterChart) {
      const ds = waterChart.data.datasets[WATER_NODES.length];
      if (ds) ds.data.push(...wAnom);
    }

    // --- Power ---
    const pVals = POWER_NODES.map(n => {
      const nd = power[n];
      return nd ? (nd.vm_pu ?? nd.value ?? null) : null;
    });
    _push(powerChart, POWER_NODES.length, tick, pVals);

    // --- Traffic ---
    const tVals = TRAFFIC_NODES.map(n => {
      const nd = traffic[n];
      return nd ? (nd.vehicle_flow ?? nd.value ?? null) : null;
    });
    _push(trafficChart, TRAFFIC_NODES.length, tick, tVals);

    // --- Event lines ---
    if ((payload.cusum_alerts || []).length) {
      _addVLine('water', tick, C.amber, 'CUSUM');
      _addVLine('power', tick, C.amber, 'CUSUM');
    }
    if (payload.isoforest_alert) {
      _addVLine('water', tick, C.purple, 'IF');
      _addVLine('power', tick, C.purple, 'IF');
    }
    if (payload.mode_a?.confidence >= 0.75) {
      _addVLine('water', tick, C.red, 'ME-DT', []);
      _addVLine('power', tick, C.red, 'ME-DT', []);
    }

    // --- Panel state annotations ---
    const waterHammer = (payload.violations || []).some(v => v.rule_id === 'W3');
    document.getElementById('chart-water-panel')?.style.setProperty(
      'background', waterHammer ? 'rgba(239,68,68,0.04)' : ''
    );
    document.getElementById('annotation-water')?.classList.toggle('visible', waterHammer);

    const ieeeViolation = (payload.violations || []).some(v => v.rule_id === 'P1' || v.rule_id === 'P2');
    document.getElementById('annotation-power')?.classList.toggle('visible', ieeeViolation);
  }

  return { init, update };
})();
