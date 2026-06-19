/**
 * city_map.js — Infrastructure Topology / Surveillance Overlay
 * Water: pipe junctions  |  Power: substations  |  Traffic: camera icons
 */

const CityMap = (() => {
  const SVG_NS = 'http://www.w3.org/2000/svg';
  let svg = null;
  let tooltip = null;
  let objLayer = null;     // HTML overlay for 3D object figures
  let figures = {};        // node_id -> { root, label, reading, type, status }
  let openInspectId = null;
  let nodeData = {};
  let nodeStatus = {};

  const WATER_NODES   = ['10','15','20','35','40','50','115','117'];
  const POWER_NODES   = ['0','4','8','12','18','32'];
  const TRAFFIC_NODES = ['SYN-T01','SYN-T02','SYN-T03','SYN-T04','SYN-T05','SYN-T06'];

  const WATER_POS = {
    '10':  {x:8,  y:12}, '15': {x:16, y:22}, '20': {x:8,  y:32},
    '35':  {x:18, y:38}, '40': {x:8,  y:48}, '50': {x:18, y:55},
    '115': {x:28, y:28}, '117':{x:28, y:42},
  };
  const POWER_POS = {
    '0':  {x:58, y:10}, '4': {x:66, y:18}, '8':  {x:74, y:26},
    '12': {x:66, y:34}, '18':{x:74, y:10}, '32': {x:80, y:42},
  };
  const TRAFFIC_POS = {
    'SYN-T01':{x:35, y:68}, 'SYN-T02':{x:46, y:72}, 'SYN-T03':{x:57, y:68},
    'SYN-T04':{x:35, y:78}, 'SYN-T05':{x:46, y:82}, 'SYN-T06':{x:57, y:78},
  };

  // Colors — hex equivalents of OKLCH tokens
  const COL = {
    water:   '#5a8fba',  // oklch(60% 0.09 215)
    power:   '#d4923a',  // oklch(68% 0.15 68)
    traffic: '#5a5550',  // oklch(42% 0.04 28)
    hal:     '#c03330',  // oklch(52% 0.18 28)
    alert:   '#d93d30',  // oklch(62% 0.22 28)
    amber:   '#d4923a',
    grid:    '#8a2820',
  };

  const ZONES = {
    water:   {x:3,  y:5,  w:32, h:55, color:COL.water,   label:'WATER ZONE'},
    power:   {x:52, y:5,  w:33, h:55, color:COL.power,   label:'POWER ZONE'},
    traffic: {x:28, y:62, w:36, h:22, color:COL.traffic,  label:'SURVEILLANCE / SYNTHETIC'},
  };

  function el(tag, attrs={}) {
    const e = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    return e;
  }

  // -----------------------------------------------------------------------
  // Init
  // -----------------------------------------------------------------------
  function init(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    svg = el('svg', {
      viewBox: '0 0 100 90',
      preserveAspectRatio: 'xMidYMid meet',
      id: 'city-map',
      style: 'width:100%;height:100%;',
    });
    container.appendChild(svg);

    tooltip = document.getElementById('node-tooltip') || document.createElement('div');

    _addDefs();
    _drawGrid();
    _drawZones();
    _drawCoverageArcs();
    _drawCrossZoneLinks();
    _drawNodes();
    _drawScanBeam();
    _drawVignette();

    // HTML 3D object overlay sits on top of the finished SVG topology
    _mountObjectFigures(containerId);
  }

  // -----------------------------------------------------------------------
  // SVG defs: vignette gradient
  // -----------------------------------------------------------------------
  function _addDefs() {
    const defs = el('defs');
    const grad = el('radialGradient', {
      id: 'vigGrad', cx: '50', cy: '45', r: '65',
      gradientUnits: 'userSpaceOnUse',
    });
    const s1 = el('stop', {offset: '35%', 'stop-color': 'rgba(0,0,0,0)'});
    const s2 = el('stop', {offset: '100%', 'stop-color': '#090608', 'stop-opacity': '0.55'});
    grad.appendChild(s1);
    grad.appendChild(s2);
    defs.appendChild(grad);
    svg.appendChild(defs);
  }

  // -----------------------------------------------------------------------
  // Grid overlay — surveillance coordinate system
  // -----------------------------------------------------------------------
  function _drawGrid() {
    const g = el('g', {opacity: '0.06'});
    for (let x = 0; x <= 100; x += 10) {
      g.appendChild(el('line', {x1:x, y1:0, x2:x, y2:90, stroke:COL.grid, 'stroke-width':0.2}));
    }
    for (let y = 0; y <= 90; y += 10) {
      g.appendChild(el('line', {x1:0, y1:y, x2:100, y2:y, stroke:COL.grid, 'stroke-width':0.2}));
    }
    // Coordinate labels at grid intersections (sparse)
    [[10,10],[50,50],[90,10],[90,80]].forEach(([x,y]) => {
      const t = el('text', {x:x+0.5, y:y+1.5, fill:COL.grid, 'font-size':1.5,
        'font-family':"'JetBrains Mono',monospace", opacity:'0.6'});
      t.textContent = `${x}:${y}`;
      g.appendChild(t);
    });
    svg.appendChild(g);
  }

  // -----------------------------------------------------------------------
  // Camera coverage arcs — surveillance reach circles
  // -----------------------------------------------------------------------
  function _drawCoverageArcs() {
    for (const pos of Object.values(TRAFFIC_POS)) {
      const arc = el('circle', {
        cx: pos.x, cy: pos.y, r: 11,
        fill: COL.traffic, opacity: '0.035',
        stroke: COL.traffic, 'stroke-width': 0.25, 'stroke-dasharray': '1.5 2.5',
      });
      svg.appendChild(arc);
    }
  }

  // -----------------------------------------------------------------------
  // Zone rectangles
  // -----------------------------------------------------------------------
  function _drawZones() {
    const counts = { water: WATER_NODES.length, power: POWER_NODES.length, traffic: TRAFFIC_NODES.length };

    for (const [key, z] of Object.entries(ZONES)) {
      const rect = el('rect', {
        x: z.x, y: z.y, width: z.w, height: z.h,
        rx: 0, ry: 0,
        fill: 'none', stroke: z.color, 'stroke-width': 0.35,
        'stroke-dasharray': key === 'traffic' ? '2 1.2' : 'none',
        opacity: '0.40',
      });
      svg.appendChild(rect);

      // Zone label (top-left)
      const lbl = el('text', {
        x: z.x + 1, y: z.y + 3.2,
        fill: z.color, 'font-size': 2.0,
        'font-family': "'JetBrains Mono', monospace",
        'font-weight': '700',
        opacity: '0.85',
      });
      lbl.textContent = z.label;
      svg.appendChild(lbl);

      // Node count (top-right)
      const cnt = el('text', {
        x: z.x + z.w - 0.8, y: z.y + 3.2,
        fill: z.color, 'font-size': 1.8,
        'font-family': "'JetBrains Mono', monospace",
        'text-anchor': 'end',
        opacity: '0.55',
      });
      cnt.textContent = counts[key] + ' nodes';
      svg.appendChild(cnt);
    }

    // Synthetic warning
    const warn = el('text', {
      x: 29, y: 67.2,
      fill: COL.amber, 'font-size': 1.7,
      'font-family': "'JetBrains Mono', monospace",
      'font-weight': '700', opacity: '0.7',
    });
    warn.textContent = 'SYNTHETIC DATA';
    svg.appendChild(warn);
  }

  // -----------------------------------------------------------------------
  // Cross-zone connection lines (inter-domain dependencies)
  // -----------------------------------------------------------------------
  function _drawCrossZoneLinks() {
    const lineAttrs = (x1,y1,x2,y2) => ({
      x1,y1,x2,y2, stroke:'#7a3020', 'stroke-width':0.4,
      'stroke-dasharray':'1.5 1', opacity:'0.45',
    });
    svg.appendChild(el('line', lineAttrs(36,35, 52,30)));
    svg.appendChild(el('line', lineAttrs(68,60, 57,66)));
    svg.appendChild(el('line', lineAttrs(18,60, 35,70)));
  }

  // -----------------------------------------------------------------------
  // Intra-zone link lines
  // -----------------------------------------------------------------------
  function _drawIntraLinks(positions, color) {
    const ids = Object.keys(positions);
    for (let i = 0; i < ids.length - 1; i++) {
      const a = positions[ids[i]], b = positions[ids[i+1]];
      svg.appendChild(el('line', {
        x1:a.x, y1:a.y, x2:b.x, y2:b.y,
        stroke:color, 'stroke-width':0.25, opacity:'0.28',
      }));
    }
  }

  // -----------------------------------------------------------------------
  // Node rendering — SVG draws ONLY the pipe/link topology now.
  // The 3D object figures live in an HTML overlay (see _mountObjectFigures).
  // -----------------------------------------------------------------------
  function _drawNodes() {
    _drawIntraLinks(WATER_POS,   COL.water);
    _drawIntraLinks(POWER_POS,   COL.power);
    _drawIntraLinks(TRAFFIC_POS, COL.traffic);
  }

  // -----------------------------------------------------------------------
  // Scan beam — surveillance sweep animation
  // -----------------------------------------------------------------------
  function _drawScanBeam() {
    const beam = el('line', {
      x1: '0', y1: '0', x2: '100', y2: '0',
      stroke: COL.hal, 'stroke-width': '0.35', opacity: '0.30',
    });
    const a1 = el('animate', {attributeName:'y1', values:'0;90;0', dur:'7s', repeatCount:'indefinite'});
    const a2 = el('animate', {attributeName:'y2', values:'0;90;0', dur:'7s', repeatCount:'indefinite'});
    beam.appendChild(a1);
    beam.appendChild(a2);
    svg.appendChild(beam);
  }

  // -----------------------------------------------------------------------
  // Vignette overlay
  // -----------------------------------------------------------------------
  function _drawVignette() {
    svg.appendChild(el('rect', {
      x: '0', y: '0', width: '100', height: '90',
      fill: 'url(#vigGrad)',
      'pointer-events': 'none',
    }));
  }

  // -----------------------------------------------------------------------
  // 3D Object Figures — HTML overlay (CSS preserve-3d)
  // -----------------------------------------------------------------------
  const ALERT_STATES = new Set(['UNDER_ATTACK', 'SUSPECT']);

  // Inner markup per object type. Built once, then never re-rendered.
  const FIGURE_MARKUP = {
    pump: `
      <div class="obj-shadow-disc"></div>
      <div class="obj-base-ring"></div>
      <div class="obj-stage">
        <div class="pump-cap-bottom"></div>
      </div>
      <div class="pump-billboard">
        <div class="pump-barrel"></div>
        <div class="pump-band"></div>
      </div>
      <div class="obj-stage">
        <div class="pump-cap-top"></div>
      </div>`,
    substation: `
      <div class="obj-shadow-disc"></div>
      <div class="obj-base-ring"></div>
      <div class="obj-stage">
        <div class="sub-body">
          <div class="sub-front"></div>
          <div class="sub-top"></div>
          <div class="sub-fins">
            <div class="fin"></div><div class="fin"></div><div class="fin"></div>
          </div>
        </div>
      </div>`,
    camera: `
      <div class="obj-shadow-disc"></div>
      <div class="obj-base-ring"></div>
      <div class="cam-scan"></div>
      <div class="obj-stage">
        <div class="cam-body">
          <div class="cam-mount"></div>
          <div class="cam-housing"></div>
          <div class="cam-lens"></div>
          <div class="cam-led"></div>
        </div>
      </div>`,
  };

  // Geometry type drives both the CSS class (obj-{type}) and the markup.
  function _typeOf(nid) {
    if (WATER_NODES.includes(nid))   return 'pump';
    if (POWER_NODES.includes(nid))   return 'substation';
    return 'camera';
  }

  function _mountObjectFigures(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (getComputedStyle(container).position === 'static') {
      container.style.position = 'relative';
    }

    objLayer = document.createElement('div');
    objLayer.className = 'city-object-layer';
    container.appendChild(objLayer);

    const allPositions = { ...WATER_POS, ...POWER_POS, ...TRAFFIC_POS };
    for (const [nid, pos] of Object.entries(allPositions)) {
      const type = _typeOf(nid);
      const fig = document.createElement('div');
      fig.className = `obj-figure obj-${type}`;
      // viewBox is 100 × 90 → percentage of the overlay box
      fig.style.left = (pos.x / 100 * 100) + '%';
      fig.style.top  = (pos.y / 90  * 100) + '%';
      fig.dataset.node = nid;

      const label = document.createElement('div');
      label.className = 'obj-label';
      label.textContent = nid;
      const reading = document.createElement('span');
      reading.className = 'obj-reading';
      reading.textContent = '—';
      label.appendChild(reading);

      fig.innerHTML = FIGURE_MARKUP[type];
      fig.appendChild(label);

      fig.addEventListener('click', (e) => { e.stopPropagation(); _toggleInspect(nid); });
      fig.addEventListener('mouseenter', (e) => _showTooltip(e, nid));
      fig.addEventListener('mousemove',  (e) => _moveTooltip(e));
      fig.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });

      objLayer.appendChild(fig);
      figures[nid] = { root: fig, label, reading, type, status: 'NORMAL' };
    }

    // Dismiss inspect panel on outside click
    document.addEventListener('click', () => { if (openInspectId) _closeInspect(); });
  }

  // -----------------------------------------------------------------------
  // Public: incremental figure update (no re-render)
  // -----------------------------------------------------------------------
  function updateFigure(nodeId, status, reading) {
    const f = figures[nodeId];
    if (!f) return;

    if (reading !== undefined && reading !== null && reading !== '') {
      if (f.reading.textContent !== reading) f.reading.textContent = reading;
    }

    if (f.status !== status) {
      f.status = status;
      _applyFigureState(f, status);
      if (openInspectId === nodeId) _renderInspect(nodeId);  // live-refresh open card
    }
  }

  function _applyFigureState(f, status) {
    const cl = f.root.classList;
    cl.toggle('alert', ALERT_STATES.has(status));
    cl.toggle('quarantined', status === 'QUARANTINED');
  }

  // -----------------------------------------------------------------------
  // Inspect panel — click-to-open detail card near the figure
  // -----------------------------------------------------------------------
  function _readingFor(nid) {
    const d = nodeData[nid] || {};
    if (d.value !== undefined)        return `${Number(d.value).toFixed(2)} ${d.unit || 'm'}`;
    if (d.vm_pu !== undefined)        return `${Number(d.vm_pu).toFixed(4)} pu`;
    if (d.vehicle_flow !== undefined) return `${d.vehicle_flow} veh/min`;
    return '—';
  }

  function _toggleInspect(nid) {
    if (openInspectId === nid) { _closeInspect(); return; }
    _renderInspect(nid);
  }

  function _closeInspect() {
    const p = objLayer && objLayer.querySelector('.inspect-panel');
    if (p) p.remove();
    openInspectId = null;
  }

  function _renderInspect(nid) {
    _closeInspect();
    const f = figures[nid];
    if (!f || !objLayer) return;
    const d = nodeData[nid] || {};
    const status = f.status || d.status || 'NORMAL';
    const kindLabel = { pump: 'Pump / Junction', substation: 'Substation', camera: 'CCTV Node' }[f.type];
    const metricLabel = f.type === 'pump' ? 'Pressure'
                      : f.type === 'substation' ? 'Voltage' : 'Detections';

    const panel = document.createElement('div');
    panel.className = 'inspect-panel';
    panel.style.left = f.root.style.left;
    panel.style.top  = f.root.style.top;
    panel.style.transform = 'translate(18px, -8px)';
    panel.addEventListener('click', (e) => e.stopPropagation());
    panel.innerHTML = `
      <button class="inspect-close" aria-label="Close">×</button>
      <div class="inspect-head">
        <span class="inspect-id">${nid}</span>
        <span class="inspect-kind">${kindLabel}</span>
      </div>
      <div class="inspect-row"><span class="k">${metricLabel}</span><span class="v">${_readingFor(nid)}</span></div>
      ${d.subsystem ? `<div class="inspect-row"><span class="k">Subsystem</span><span class="v">${d.subsystem}</span></div>` : ''}
      ${d.source ? `<div class="inspect-row"><span class="k">Source</span><span class="v">${d.source}</span></div>` : ''}
      <span class="inspect-badge s-${status}">${status.replace('_', ' ')}</span>
    `;
    panel.querySelector('.inspect-close').addEventListener('click', (e) => { e.stopPropagation(); _closeInspect(); });
    objLayer.appendChild(panel);
    openInspectId = nid;
  }

  // -----------------------------------------------------------------------
  // Tooltip
  // -----------------------------------------------------------------------
  function _showTooltip(e, nid) {
    const d = nodeData[nid] || {};
    tooltip.innerHTML = `
      <strong style="color:var(--hal)">${nid}</strong><br>
      ${d.subsystem ? `<span style="color:var(--text-muted)">Subsystem:</span> ${d.subsystem}<br>` : ''}
      ${d.value !== undefined ? `<span style="color:var(--text-muted)">Value:</span> ${Number(d.value).toFixed(3)} ${d.unit||''}<br>` : ''}
      ${d.vm_pu !== undefined ? `<span style="color:var(--text-muted)">Voltage:</span> ${Number(d.vm_pu).toFixed(4)} pu<br>` : ''}
      ${d.vehicle_flow !== undefined ? `<span style="color:var(--text-muted)">Flow:</span> ${d.vehicle_flow} veh/min<br>` : ''}
      ${d.status ? `<span style="color:var(--text-muted)">Status:</span> <span style="color:${_statusColor(d.status)}">${d.status}</span><br>` : ''}
      ${d.source ? `<span style="color:var(--text-muted)">Source:</span> ${d.source}` : ''}
    `;
    tooltip.style.display = 'block';
    _moveTooltip(e);
  }

  function _moveTooltip(e) {
    tooltip.style.left = (e.clientX + 12) + 'px';
    tooltip.style.top  = (e.clientY - 10) + 'px';
  }

  function _statusColor(status) {
    return { NORMAL:'#2d9e72', SUSPECT:'#d4923a', QUARANTINED:'#c03330', UNDER_ATTACK:'#d93d30' }[status] || '#4a4843';
  }

  // -----------------------------------------------------------------------
  // Public: update from WS payload
  // -----------------------------------------------------------------------
  function update(twState) {
    const all = { ...twState.water, ...twState.power, ...twState.traffic };
    for (const [nid, nd] of Object.entries(all)) {
      nodeData[nid] = nd;
      const status = nd.status || 'NORMAL';
      // Incremental: updateFigure only touches the DOM when something changed.
      updateFigure(nid, status, _readingFor(nid));
      nodeStatus[nid] = status;
    }
  }

  // -----------------------------------------------------------------------
  // Public: attack propagation arcs
  // -----------------------------------------------------------------------
  function animateAttack(entryNodeId, affectedNodes) {
    const positions = { ...WATER_POS, ...POWER_POS, ...TRAFFIC_POS };
    const src = positions[entryNodeId];
    if (!src) return;
    for (const nid of affectedNodes) {
      const dst = positions[nid];
      if (!dst) continue;
      const arc = el('line', {
        x1: src.x, y1: src.y, x2: dst.x, y2: dst.y,
        stroke: COL.alert, 'stroke-width': 0.8, opacity: '0.9',
        'stroke-dasharray': '2 1',
      });
      svg.appendChild(arc);
      const anim = el('animate', {
        attributeName: 'opacity', from: '0.9', to: '0',
        dur: '2s', begin: '0s', fill: 'freeze',
      });
      arc.appendChild(anim);
      setTimeout(() => arc.remove(), 5000);
    }
  }

  return { init, update, updateFigure, animateAttack };
})();
