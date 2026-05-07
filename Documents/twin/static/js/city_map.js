/**
 * city_map.js — Infrastructure Topology / Surveillance Overlay
 * Water: pipe junctions  |  Power: substations  |  Traffic: camera icons
 */

const CityMap = (() => {
  const SVG_NS = 'http://www.w3.org/2000/svg';
  let svg = null;
  let tooltip = null;
  let nodeElements = {};   // node_id -> { g, circle (glow), label }
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
  // Icon factories
  // -----------------------------------------------------------------------
  function _makeWaterIcon(pos, color) {
    const g = el('g');
    g.appendChild(el('line', {x1:pos.x-2.2,y1:pos.y, x2:pos.x+2.2,y2:pos.y, stroke:color,'stroke-width':0.65}));
    g.appendChild(el('line', {x1:pos.x,y1:pos.y-2.2, x2:pos.x,y2:pos.y+2.2, stroke:color,'stroke-width':0.65}));
    g.appendChild(el('circle', {cx:pos.x,cy:pos.y, r:0.85, fill:color}));
    return g;
  }

  function _makePowerIcon(pos, color) {
    const g = el('g');
    g.appendChild(el('rect', {x:pos.x-1.7,y:pos.y-1.7, width:3.4,height:3.4,
      fill:'none', stroke:color,'stroke-width':0.45}));
    g.appendChild(el('line', {x1:pos.x-1.2,y1:pos.y-1.2, x2:pos.x+1.2,y2:pos.y+1.2,
      stroke:color,'stroke-width':0.3,opacity:'0.50'}));
    g.appendChild(el('line', {x1:pos.x+1.2,y1:pos.y-1.2, x2:pos.x-1.2,y2:pos.y+1.2,
      stroke:color,'stroke-width':0.3,opacity:'0.50'}));
    g.appendChild(el('circle', {cx:pos.x,cy:pos.y, r:0.65, fill:color}));
    return g;
  }

  function _makeCameraIcon(pos, color) {
    const g = el('g');
    // Body
    g.appendChild(el('rect', {x:pos.x-2.3,y:pos.y-1.4, width:4.0,height:2.8,
      rx:'0.25', fill:color, opacity:'0.88'}));
    // Lens ring
    g.appendChild(el('circle', {cx:pos.x-0.4,cy:pos.y, r:1.05,
      fill:'none', stroke:'rgba(0,0,0,0.55)','stroke-width':0.4}));
    // Lens glass
    g.appendChild(el('circle', {cx:pos.x-0.4,cy:pos.y, r:0.45, fill:color, opacity:'0.65'}));
    // Viewfinder bump
    g.appendChild(el('rect', {x:pos.x+1.3,y:pos.y-2.1, width:1.0,height:0.85,
      rx:'0.15', fill:color, opacity:'0.65'}));
    return g;
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
  // Node rendering
  // -----------------------------------------------------------------------
  function _drawNodes() {
    _drawIntraLinks(WATER_POS,   COL.water);
    _drawIntraLinks(POWER_POS,   COL.power);
    _drawIntraLinks(TRAFFIC_POS, COL.traffic);

    const allPositions = { ...WATER_POS, ...POWER_POS, ...TRAFFIC_POS };

    for (const [nid, pos] of Object.entries(allPositions)) {
      const subsystem = WATER_NODES.includes(nid) ? 'water'
                      : POWER_NODES.includes(nid) ? 'power' : 'traffic';
      const color = COL[subsystem];

      const g = el('g', { class: `node-group node-${nid}`, cursor: 'pointer' });

      // Glow circle — status indicator behind icon
      const glow = el('circle', {
        cx: pos.x, cy: pos.y, r: '2.6',
        fill: color, opacity: '0.14', stroke: 'none',
        class: 'node-circle',
        'data-node': nid,
        'data-subsystem': subsystem,
      });
      glow.style.animation = 'pulse-normal 2s infinite';
      g.appendChild(glow);

      // Typed icon
      const icon = subsystem === 'water' ? _makeWaterIcon(pos, color)
                 : subsystem === 'power' ? _makePowerIcon(pos, color)
                 : _makeCameraIcon(pos, color);
      g.appendChild(icon);

      // Label
      const label = el('text', {
        x: pos.x, y: pos.y + 4.2,
        'text-anchor': 'middle',
        fill: color, 'font-size': '1.75',
        'font-family': "'JetBrains Mono', monospace",
        opacity: '0.60',
      });
      label.textContent = nid;
      g.appendChild(label);

      g.addEventListener('mouseenter', (e) => _showTooltip(e, nid));
      g.addEventListener('mousemove',  (e) => _moveTooltip(e));
      g.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });

      svg.appendChild(g);
      nodeElements[nid] = { g, circle: glow, label };
    }
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
  // Node state application
  // -----------------------------------------------------------------------
  function _applyNodeState(nid, status) {
    const els = nodeElements[nid];
    if (!els) return;
    const { circle: glow } = els;
    const subsystem = nid.startsWith('SYN') ? 'traffic'
                    : POWER_NODES.includes(nid) ? 'power' : 'water';
    const defaultFill = COL[subsystem];

    glow.style.animation = '';

    switch (status) {
      case 'NORMAL':
        glow.setAttribute('r', '2.6');
        glow.setAttribute('fill', defaultFill);
        glow.setAttribute('opacity', '0.14');
        glow.style.animation = 'pulse-normal 2s infinite';
        _removeXOverlay(nid);
        break;
      case 'SUSPECT':
        glow.setAttribute('r', '3.4');
        glow.setAttribute('fill', COL.amber);
        glow.setAttribute('opacity', '0.38');
        glow.style.animation = 'pulse-suspect 0.8s infinite';
        _removeXOverlay(nid);
        break;
      case 'QUARANTINED':
        glow.setAttribute('r', '3.4');
        glow.setAttribute('fill', COL.hal);
        glow.setAttribute('opacity', '0.44');
        glow.style.animation = 'none';
        _addXOverlay(nid, els);
        break;
      case 'UNDER_ATTACK':
        glow.setAttribute('r', '4.0');
        glow.setAttribute('fill', COL.alert);
        glow.setAttribute('opacity', '0.52');
        glow.style.animation = 'blink-attack 0.3s infinite';
        _removeXOverlay(nid);
        break;
    }
  }

  function _addXOverlay(nid, els) {
    if (document.getElementById(`x-${nid}`)) return;
    const pos = { ...WATER_POS, ...POWER_POS, ...TRAFFIC_POS }[nid];
    if (!pos) return;
    const xg = el('g', { id: `x-${nid}` });
    xg.appendChild(el('line', {x1:pos.x-1.8,y1:pos.y-1.8, x2:pos.x+1.8,y2:pos.y+1.8,
      stroke:'white','stroke-width':0.5, opacity:'0.7'}));
    xg.appendChild(el('line', {x1:pos.x+1.8,y1:pos.y-1.8, x2:pos.x-1.8,y2:pos.y+1.8,
      stroke:'white','stroke-width':0.5, opacity:'0.7'}));
    const badge = el('text', {
      x: pos.x, y: pos.y-3.2, 'text-anchor': 'middle',
      fill: COL.hal, 'font-size': '1.8',
      'font-family': "'JetBrains Mono', monospace", 'font-weight': '700',
    });
    badge.textContent = 'ISOLATED';
    xg.appendChild(badge);
    svg.appendChild(xg);
  }

  function _removeXOverlay(nid) {
    const x = document.getElementById(`x-${nid}`);
    if (x) x.remove();
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
      if (nodeStatus[nid] !== status) {
        nodeStatus[nid] = status;
        _applyNodeState(nid, status);
      }
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

  return { init, update, animateAttack };
})();
