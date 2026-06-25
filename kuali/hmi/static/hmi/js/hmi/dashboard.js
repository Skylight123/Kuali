(() => {
  'use strict';

  // ── MODBUS ADDRESS MAP ─────────────────────────────────────────────────────
  // Sesuaikan nilai integer ini dengan register PLC aktual
  const ADDR = {
    STIRRER_1:  1,
    STIRRER_2:  2,
    CONVEYOR_1: 3,
    CONVEYOR_2: 4,
    CONVEYOR_3: 5,
    CONVEYOR_4: 6,
    CONVEYOR_5: 7,
    CONVEYOR_6: 8,
    CMD_9:      9,
    CMD_10:     10,
  };

  // ── CONVEYOR DEFINITIONS (3 group) ─────────────────────────────────────────
  const GROUPS = [
    {
      label: 'Mie',
      conveyors: [
        { id: 1, name: 'Mie', addr: ADDR.CONVEYOR_1, color: '#dcc06a' },
      ],
    },
    {
      label: 'Sauce',
      conveyors: [
        { id: 2, name: 'Sauce 1', addr: ADDR.CONVEYOR_2, color: '#d6453e' },
        { id: 3, name: 'Sauce 2', addr: ADDR.CONVEYOR_3, color: '#e8843a' },
      ],
    },
    {
      label: 'Topping',
      conveyors: [
        { id: 4, name: 'Topping 1', addr: ADDR.CONVEYOR_4, color: '#54b85c' },
        { id: 5, name: 'Topping 2', addr: ADDR.CONVEYOR_5, color: '#46b8e0' },
        { id: 6, name: 'Topping 3', addr: ADDR.CONVEYOR_6, color: '#b879e0' },
      ],
    },
  ];
  const ALL_CONVEYORS = GROUPS.flatMap((g) => g.conveyors);

  const COOKERS = [{ id: 1, cx: 390 }, { id: 2, cx: 770 }];

  // ── PLANT STATE ─────────────────────────────────────────────────────────────
  const state = {
    ws: 'connecting',   // 'connecting' | 'ok' | 'error'
    registers: {},      // address(int) → value(int) — filled by WebSocket
    alarms: [],
    alarmId: 0,
  };

  // ── SVG REFS ────────────────────────────────────────────────────────────────
  const refs = { paddle: {}, tread: {}, ring: {}, steam: {}, heat: {}, mini: {} };
  const beltOffset = {};
  ALL_CONVEYORS.forEach((c) => { beltOffset[c.id] = 0; });

  // ── SVG HELPERS ─────────────────────────────────────────────────────────────
  const NS = 'http://www.w3.org/2000/svg';
  const $ = (sel) => document.querySelector(sel);
  const make = (tag, attrs, parent) => {
    const el = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
    if (parent) parent.appendChild(el);
    return el;
  };
  const txt = (parent, x, y, content, cls) => {
    const el = make('text', { x, y, class: cls || 'mimic-label' }, parent);
    el.textContent = content;
    return el;
  };

  // ── BUILD MIMIC SVG ─────────────────────────────────────────────────────────
  const BELT_X0 = 190;
  const BELT_X1 = 990;
  const BELT_TREAD = 22;
  const LANE_Y = (i) => 88 + i * 72;   // 6 lanes
  const WOK_Y = 610;

  function buildMimic() {
    const host = $('#mimicHost');
    const svg = make('svg', { viewBox: '0 0 1160 780', role: 'img', 'aria-label': 'Digital twin Kuali' });
    host.appendChild(svg);

    const defs = make('defs', {}, svg);
    defs.innerHTML = `
      <linearGradient id="zkSteel" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0"    stop-color="#7a6a58"/>
        <stop offset="0.5"  stop-color="#4e4030"/>
        <stop offset="1"    stop-color="#32261a"/>
      </linearGradient>
      <radialGradient id="zkBowl" cx="50%" cy="36%" r="70%">
        <stop offset="0" stop-color="#1e1510"/>
        <stop offset="1" stop-color="#080502"/>
      </radialGradient>
      <radialGradient id="zkHeat" cx="50%" cy="50%" r="50%">
        <stop offset="0"    stop-color="#e07030"/>
        <stop offset="0.55" stop-color="#c55018" stop-opacity=".48"/>
        <stop offset="1"    stop-color="#c55018" stop-opacity="0"/>
      </radialGradient>
      ${COOKERS.map((c) => `
        <clipPath id="sc${c.id}" clipPathUnits="userSpaceOnUse">
          <ellipse cx="${c.cx}" cy="${WOK_Y}" rx="80" ry="21"/>
        </clipPath>`).join('')}
    `;

    // Section labels (far left)
    txt(svg, 12, LANE_Y(0) + 4,  'MIE',     'group-label');
    txt(svg, 12, LANE_Y(1) + 4,  'SAUCE',   'group-label');
    txt(svg, 12, LANE_Y(3) + 4,  'TOPPING', 'group-label');

    // Group separator lines
    const sepY = [LANE_Y(0) + 36, LANE_Y(2) + 36];
    sepY.forEach((y) => make('line', { x1: BELT_X0, y1: y, x2: BELT_X1, y2: y, class: 'group-sep' }, svg));

    // Vertical chutes per cooker
    COOKERS.forEach((ck) => {
      make('rect', {
        x: ck.cx - 10,
        y: LANE_Y(5) + 12,
        width: 20,
        height: WOK_Y - LANE_Y(5) - 12,
        rx: 6,
        fill: '#100905',
        stroke: '#2d2018',
        'stroke-width': 1,
      }, svg);
    });

    // Conveyor lanes
    ALL_CONVEYORS.forEach((cv, i) => {
      const y = LANE_Y(i);

      // Belt track
      make('rect', { x: BELT_X0, y: y - 9, width: BELT_X1 - BELT_X0, height: 18, rx: 9, class: 'belt-shell' }, svg);

      // Tread marks
      const tread = make('g', { class: 'belt-tread' }, svg);
      for (let x = BELT_X0 - BELT_TREAD; x < BELT_X1 + BELT_TREAD; x += BELT_TREAD) {
        make('line', { x1: x, y1: y - 9, x2: x - 7, y2: y + 9 }, tread);
      }
      refs.tread[cv.id] = { node: tread, offset: 0 };

      // Belt active color overlay
      const belt_active = make('rect', {
        id: `belt-active-${cv.id}`,
        x: BELT_X0 + 2, y: y - 7, width: BELT_X1 - BELT_X0 - 4, height: 14,
        rx: 7, fill: cv.color, opacity: 0,
        style: 'transition: opacity .2s',
      }, svg);
      refs.tread[cv.id].active = belt_active;

      // Lane name label (left)
      txt(svg, BELT_X0 - 12, y + 4, cv.name.toUpperCase(), 'mimic-label').setAttribute('text-anchor', 'end');

      // Lane ID label (right)
      txt(svg, BELT_X1 + 14, y + 4, `C${cv.id}`, 'mimic-label');

      // Drop arrows into cookers
      COOKERS.forEach((ck) => {
        make('path', {
          d: `M${ck.cx - 7} ${y + 9} L${ck.cx + 7} ${y + 9} L${ck.cx} ${y + 20} Z`,
          fill: '#1f1610', stroke: '#352a20', 'stroke-width': 1,
          id: `gate-${cv.id}-${ck.id}`,
        }, svg);
      });
    });

    // Cooker labels
    COOKERS.forEach((ck) => {
      txt(svg, ck.cx, WOK_Y + 112, `COOKER ${ck.id}`, 'mimic-label').setAttribute('text-anchor', 'middle');
      drawCooker(svg, ck);
    });
  }

  function drawCooker(svg, cooker) {
    const { cx } = cooker;
    const cy = WOK_Y;

    // Heat glow (below body)
    refs.heat[cooker.id] = make('ellipse', {
      cx, cy: cy + 84, rx: 88, ry: 30,
      fill: 'url(#zkHeat)', opacity: 0,
      style: 'transition: opacity .4s',
    }, svg);

    // Body trapezoid
    make('path', {
      d: `M${cx - 94} ${cy + 34} L${cx + 94} ${cy + 34} L${cx + 80} ${cy + 92} L${cx - 80} ${cy + 92} Z`,
      fill: 'url(#zkSteel)', class: 'cooker-body',
    }, svg);

    // Outer rim ellipse
    make('ellipse', { cx, cy, rx: 90, ry: 27, fill: 'url(#zkSteel)', class: 'cooker-body' }, svg);

    // Inner bowl (dark)
    make('ellipse', { cx, cy, rx: 80, ry: 21, fill: 'url(#zkBowl)' }, svg);

    // Status ring
    refs.ring[cooker.id] = make('ellipse', {
      cx, cy, rx: 93, ry: 30, class: 'cooker-ring',
    }, svg);

    // ── STIRRER — clipped to inner bowl ────────────────────────────────────
    const paddle = make('g', {
      class: 'paddle',
      'clip-path': `url(#sc${cooker.id})`,
    }, svg);

    // Horizontal arm (cream/white)
    make('rect', {
      x: cx - 78, y: cy - 5, width: 156, height: 10, rx: 5,
      fill: '#d4c5ae', opacity: .84,
    }, paddle);

    // Vertical arm (gold)
    make('rect', {
      x: cx - 5, y: cy - 78, width: 10, height: 156, rx: 5,
      fill: '#c9912a', opacity: .72,
    }, paddle);

    // Center hub
    make('circle', { cx, cy, r: 8, fill: '#e7b15a' }, paddle);

    refs.paddle[cooker.id] = { node: paddle, cx, cy, angle: 0 };

    // Steam wisps
    const steam = make('g', { class: 'steam', style: 'opacity:0' }, svg);
    [-24, 0, 24].forEach((dx) => {
      make('path', { d: `M${cx + dx} ${cy - 10} q-8 -18 0 -34 q8 -16 0 -30` }, steam);
    });
    refs.steam[cooker.id] = steam;

    // Temp / state mini-label inside bowl
    const label = make('text', {
      x: cx, y: cy + 8, class: 'mimic-label',
      'text-anchor': 'middle', style: 'font-size:14px',
    }, svg);
    label.textContent = '--';
    refs.mini[cooker.id] = label;
  }

  // ── BUILD COOKER CARDS (monitor only, no simulation controls) ───────────────
  function buildCookerCards() {
    const host = $('#cookerCards');
    host.innerHTML = '';
    COOKERS.forEach((ck) => {
      const card = document.createElement('article');
      card.className = 'cooker-card';
      card.id = `card-${ck.id}`;
      card.dataset.state = 'IDLE';
      card.innerHTML = `
        <div class="card-head">
          <strong>COOKER ${ck.id}</strong>
          <span class="state-pill" id="pill-${ck.id}" data-state="IDLE">IDLE</span>
        </div>
        <div class="readouts">
          <div class="readout">
            <small>Stirrer</small>
            <strong id="stir-${ck.id}">OFF</strong>
          </div>
          <div class="readout">
            <small>Addr Modbus</small>
            <strong>${ADDR['STIRRER_' + ck.id]}</strong>
          </div>
          <div class="readout">
            <small>Status</small>
            <strong id="stir-status-${ck.id}">—</strong>
          </div>
        </div>`;
      host.appendChild(card);
    });
  }

  // ── BUILD CONVEYOR CARDS (grouped) ──────────────────────────────────────────
  function buildConveyors() {
    const host = $('#conveyorGrid');
    host.innerHTML = '';
    GROUPS.forEach((group) => {
      const groupEl = document.createElement('div');
      groupEl.className = 'conv-group';

      const labelEl = document.createElement('p');
      labelEl.className = 'conv-group-label';
      labelEl.textContent = group.label;
      groupEl.appendChild(labelEl);

      const cardsEl = document.createElement('div');
      cardsEl.className = 'conv-cards';
      group.conveyors.forEach((cv) => {
        const card = document.createElement('article');
        card.className = 'conveyor-card';
        card.id = `conv-${cv.id}`;
        card.innerHTML = `
          <div class="conveyor-top">
            <span class="swatch" style="background:${cv.color}"></span>
            <strong>${cv.name}</strong>
            <small>C${cv.id} · addr ${cv.addr}</small>
          </div>
          <div class="belt-meter">
            <i></i>
            <span id="cv-st-${cv.id}">STANDBY</span>
          </div>`;
        cardsEl.appendChild(card);
      });
      groupEl.appendChild(cardsEl);
      host.appendChild(groupEl);
    });
  }

  // ── BUILD COMMAND PANEL (addr 9 & 10) ───────────────────────────────────────
  function buildCommands() {
    const host = $('#commandPanel');
    if (!host) return;
    host.innerHTML = `
      <div class="cmd-group">
        <div class="cmd-group-label">Perintah 9 (addr ${ADDR.CMD_9})</div>
        <button type="button" class="cmd-btn is-on"  data-addr="${ADDR.CMD_9}"  data-val="1">ON</button>
        <button type="button" class="cmd-btn is-off" data-addr="${ADDR.CMD_9}"  data-val="0">OFF</button>
      </div>
      <div class="cmd-group">
        <div class="cmd-group-label">Perintah 10 (addr ${ADDR.CMD_10})</div>
        <button type="button" class="cmd-btn is-on"  data-addr="${ADDR.CMD_10}" data-val="1">ON</button>
        <button type="button" class="cmd-btn is-off" data-addr="${ADDR.CMD_10}" data-val="0">OFF</button>
      </div>`;
    host.querySelectorAll('.cmd-btn').forEach((btn) => {
      btn.addEventListener('click', () =>
        sendCommand(Number(btn.dataset.addr), Number(btn.dataset.val))
      );
    });
  }

  // ── RENDER (apply state.registers to DOM + SVG) ─────────────────────────────
  function render() {
    // WebSocket status pill
    const pill = $('#linePill');
    const lineText = $('#lineText');
    if (state.ws === 'ok') {
      pill.className = 'line-pill is-run';
      lineText.textContent = 'WS ONLINE';
    } else if (state.ws === 'error') {
      pill.className = 'line-pill is-estop';
      lineText.textContent = 'WS OFFLINE';
    } else {
      pill.className = 'line-pill is-stop';
      lineText.textContent = 'CONNECTING…';
    }

    // Alarm badge
    const openAlarms = state.alarms.filter((a) => !a.ack).length;
    $('#alarmCount').textContent = openAlarms;
    $('#alarmCount').style.color = openAlarms ? 'var(--warn)' : 'var(--run)';

    // Active stirrers / conveyors counter
    const activeStir = COOKERS.filter((ck) => Boolean(state.registers[ADDR['STIRRER_' + ck.id]])).length;
    const activeCv   = ALL_CONVEYORS.filter((cv) => Boolean(state.registers[cv.addr])).length;
    $('#activeBatch').textContent = `${activeStir}/2`;
    $('#outputCount').textContent = `${activeCv}/6`;

    // Stirrers
    COOKERS.forEach((ck) => {
      const on = Boolean(state.registers[ADDR['STIRRER_' + ck.id]]);
      const pillEl = $(`#pill-${ck.id}`);
      pillEl.dataset.state = on ? 'COOKING' : 'IDLE';
      pillEl.textContent = on ? 'JALAN' : 'IDLE';
      $(`#stir-${ck.id}`).textContent = on ? 'ON' : 'OFF';
      $(`#stir-${ck.id}`).style.color = on ? 'var(--run)' : 'var(--faint)';
      $(`#stir-status-${ck.id}`).textContent = on ? 'Berputar' : 'Berhenti';
      $(`#card-${ck.id}`).dataset.state = on ? 'COOKING' : 'IDLE';
      refs.ring[ck.id].setAttribute('stroke', on ? 'var(--clay)' : 'var(--idle)');
      refs.steam[ck.id].style.opacity = on ? 1 : 0;
      refs.heat[ck.id].style.opacity = on ? 0.7 : 0;
      refs.mini[ck.id].textContent = on ? 'ON' : '--';
    });

    // Conveyors
    ALL_CONVEYORS.forEach((cv) => {
      const on = Boolean(state.registers[cv.addr]);
      const card = $(`#conv-${cv.id}`);
      card.classList.toggle('is-running', on);
      $(`#cv-st-${cv.id}`).textContent = on ? 'RUNNING' : 'STANDBY';

      // Tint belt overlay when running
      if (refs.tread[cv.id]?.active) {
        refs.tread[cv.id].active.setAttribute('opacity', on ? 0.12 : 0);
      }

      // Drop arrow color
      COOKERS.forEach((ck) => {
        const gate = $(`#gate-${cv.id}-${ck.id}`);
        if (gate) gate.setAttribute('fill', on ? cv.color : '#1f1610');
      });
    });
  }

  // ── LOG ──────────────────────────────────────────────────────────────────────
  function log(level, source, message) {
    state.alarms.unshift({
      id: ++state.alarmId, level, source, message,
      time: new Date(),
      ack: level === 'info' || level === 'ok',
    });
    if (state.alarms.length > 120) state.alarms.pop();
    renderLog();
    render();
  }

  function renderLog() {
    $('#eventLog').innerHTML = state.alarms.slice(0, 60).map((a) => {
      const t = a.time.toLocaleTimeString('id-ID', { hour12: false });
      return `<div class="log-row" data-level="${a.level}"><time>${t}</time><i></i><span><b>${a.source}</b> — ${a.message}</span></div>`;
    }).join('');
  }

  // ── WEBSOCKET ────────────────────────────────────────────────────────────────
  let ws = null;
  let wsTimer = null;

  function connectWS() {
    if (wsTimer) { clearTimeout(wsTimer); wsTimer = null; }
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/hmi/`);
    state.ws = 'connecting';
    render();

    ws.onopen = () => {
      state.ws = 'ok';
      log('ok', 'WS', 'Terhubung ke server');
    };

    ws.onmessage = ({ data }) => {
      try {
        const payload = JSON.parse(data);
        // Expected: { "registers": { "1": 1, "2": 0, ... } }
        if (payload.registers) {
          Object.entries(payload.registers).forEach(([addr, val]) => {
            state.registers[Number(addr)] = Number(val);
          });
          render();
        }
      } catch (_) { /* ignore malformed frames */ }
    };

    ws.onclose = () => {
      state.ws = 'error';
      log('warn', 'WS', 'Koneksi terputus, mencoba ulang 5s…');
      render();
      wsTimer = setTimeout(connectWS, 5000);
    };

    ws.onerror = () => { state.ws = 'error'; render(); };
  }

  function sendCommand(address, value) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ write: { address, value } }));
      log('info', `CMD.${address}`, `Kirim nilai ${value}`);
    } else {
      log('warn', 'WS', 'Tidak terhubung — perintah tidak terkirim');
    }
  }

  // ── RAF ANIMATION LOOP ───────────────────────────────────────────────────────
  let prev = performance.now();
  function loop(now) {
    const dt = Math.min(60, now - prev);
    prev = now;

    // Rotate stirrers when ON
    COOKERS.forEach((ck) => {
      const on = Boolean(state.registers[ADDR['STIRRER_' + ck.id]]);
      const ref = refs.paddle[ck.id];
      if (on) {
        ref.angle = (ref.angle + 42 * dt / 1000) % 360;
        ref.node.setAttribute('transform', `rotate(${ref.angle} ${ref.cx} ${ref.cy})`);
      }
    });

    // Scroll belt treads when conveyor ON
    ALL_CONVEYORS.forEach((cv) => {
      const on = Boolean(state.registers[cv.addr]);
      if (!on) return;
      const ref = refs.tread[cv.id];
      beltOffset[cv.id] = (beltOffset[cv.id] - 80 * dt / 1000) % BELT_TREAD;
      ref.node.setAttribute('transform', `translate(${beltOffset[cv.id]},0)`);
    });

    requestAnimationFrame(loop);
  }

  // ── CLOCK ────────────────────────────────────────────────────────────────────
  function tick() {
    const now = new Date();
    $('#clock').textContent =
      now.toLocaleTimeString('id-ID', { hour12: false }) + ' ' +
      now.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' });
  }

  // ── INIT ─────────────────────────────────────────────────────────────────────
  buildMimic();
  buildCookerCards();
  buildConveyors();
  buildCommands();
  log('ok', 'SYSTEM', 'Kuali HMI siap');
  render();
  requestAnimationFrame(loop);
  setInterval(tick, 500);
  connectWS();

  $('#ackBtn').addEventListener('click', () => {
    state.alarms.forEach((a) => { a.ack = true; });
    renderLog();
    render();
  });

  // Public API — untuk debugging / integrasi manual
  window.KualiHMI = {
    getState: () => state,
    sendCommand,
    // Inject register values manually (e.g., for testing without PLC):
    // KualiHMI.inject({ 1: 1, 2: 0, 3: 1, 4: 1, 5: 0, 6: 0, 7: 1, 8: 0 })
    inject(regs) {
      Object.entries(regs).forEach(([k, v]) => { state.registers[Number(k)] = Number(v); });
      render();
    },
    ADDR,
  };
})();
