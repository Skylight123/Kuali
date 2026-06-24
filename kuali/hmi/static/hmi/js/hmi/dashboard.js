(() => {
    'use strict';

    const $ = (selector) => document.querySelector(selector);
    const svgNS = 'http://www.w3.org/2000/svg';
    const make = (tag, attrs, parent) => {
        const node = document.createElementNS(svgNS, tag);
        Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
        if (parent) parent.appendChild(node);
        return node;
    };
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

    const ingredients = [
        { id: 'sauce', name: 'Sauce', unit: 'ml', color: '#d6453e' },
        { id: 'veg', name: 'Sayur', unit: 'g', color: '#54b85c' },
        { id: 'protein', name: 'Protein', unit: 'g', color: '#e8843a' },
    ];
    const recipes = {
        original: { name: 'Signature Bowl', cook: 22, items: { sauce: 40, veg: 60, protein: 45 } },
        spicy: { name: 'Spicy Garlic', cook: 25, items: { sauce: 56, veg: 42, protein: 55 } },
        garden: { name: 'Garden Fresh', cook: 20, items: { sauce: 34, veg: 92, protein: 24 } },
        protein: { name: 'Protein Boost', cook: 27, items: { sauce: 44, veg: 35, protein: 78 } },
    };
    const recipeKeys = Object.keys(recipes);
    const cookers = [{ id: 1, cx: 420 }, { id: 2, cx: 760 }];
    const laneY = (index) => 135 + index * 86;
    const belt = { x0: 160, x1: 1000, tread: 24 };
    const bowlY = 520;

    const state = {
        line: 'RUN',
        auto: true,
        estop: false,
        output: 0,
        alarmId: 0,
        alarms: [],
        cookers: {},
        conveyors: {},
    };
    const refs = { tread: {}, gate: {}, chute: {}, ring: {}, heat: {}, steam: {}, paddle: {}, mini: {} };
    const particles = [];
    let particleLayer;

    cookers.forEach((cooker, index) => {
        state.cookers[cooker.id] = {
            id: cooker.id,
            state: 'IDLE',
            recipeKey: recipeKeys[index % recipeKeys.length],
            batch: 0,
            temp: 31,
            rpm: 0,
            setRpm: 46 + index * 5,
            timer: 0,
            cookTotal: 0,
            progress: 0,
            hold: false,
            doneItems: {},
            abort: false,
        };
    });
    ingredients.forEach((item) => {
        state.conveyors[item.id] = { running: false, speed: 0, target: null };
    });

    function drawText(parent, x, y, text, className) {
        const node = make('text', { x, y, class: className || 'mimic-label' }, parent);
        node.textContent = text;
        return node;
    }

    function buildMimic() {
        const host = $('#mimicHost');
        const svg = make('svg', { viewBox: '0 0 1160 680', role: 'img', 'aria-label': 'Digital twin lini masak Kuali' });
        host.appendChild(svg);

        const defs = make('defs', {}, svg);
        defs.innerHTML = `
            <linearGradient id="zkSteel" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#afbbc4"/><stop offset="0.52" stop-color="#7d8b95"/><stop offset="1" stop-color="#53616b"/>
            </linearGradient>
            <radialGradient id="zkBowl" cx="50%" cy="34%" r="70%">
                <stop offset="0" stop-color="#19252d"/><stop offset="1" stop-color="#070c10"/>
            </radialGradient>
            <radialGradient id="zkHeat" cx="50%" cy="50%" r="50%">
                <stop offset="0" stop-color="#ff8a3d"/><stop offset="0.55" stop-color="#ff5a1f" stop-opacity=".54"/><stop offset="1" stop-color="#ff5a1f" stop-opacity="0"/>
            </radialGradient>`;

        drawText(svg, 24, 32, 'BAHAN', 'mimic-label');
        drawText(svg, 470, 32, 'CONVEYOR ROUTING', 'mimic-label');
        drawText(svg, 24, 458, 'COOKER', 'mimic-label');

        cookers.forEach((cooker) => {
            make('rect', { x: cooker.cx - 30, y: 92, width: 60, height: bowlY - 92, rx: 8, class: 'chute' }, svg);
            refs.chute[cooker.id] = make('rect', { x: cooker.cx - 31, y: 92, width: 62, height: bowlY - 92, rx: 8, class: 'chute-glow' }, svg);
            drawText(svg, cooker.cx - 45, 78, `COOKER ${cooker.id}`, 'mimic-label');
        });

        ingredients.forEach((item, index) => {
            const y = laneY(index);
            make('path', { d: `M34 ${y - 24} L138 ${y - 24} L128 ${y + 14} L44 ${y + 14} Z`, class: 'hopper-shell' }, svg);
            make('rect', { x: 47, y: y - 18, width: 78, height: 26, rx: 2, fill: item.color, class: 'hopper-fill' }, svg);
            drawText(svg, 44, y - 32, item.name.toUpperCase(), 'mimic-label');

            make('rect', { x: belt.x0, y: y - 10, width: belt.x1 - belt.x0, height: 20, rx: 10, class: 'belt-shell' }, svg);
            const tread = make('g', { class: 'belt-tread' }, svg);
            for (let x = belt.x0 - belt.tread; x < belt.x1 + belt.tread; x += belt.tread) {
                make('line', { x1: x, y1: y - 10, x2: x - 8, y2: y + 10 }, tread);
            }
            refs.tread[item.id] = { node: tread, offset: 0 };

            cookers.forEach((cooker) => {
                refs.gate[`${item.id}-${cooker.id}`] = make('path', {
                    d: `M${cooker.cx - 10} ${y + 12} L${cooker.cx + 10} ${y + 12} L${cooker.cx} ${y + 25} Z`,
                    class: 'gate',
                }, svg);
            });
            drawText(svg, belt.x1 + 16, y + 4, `C-${item.id.toUpperCase()}`, 'mimic-label');
        });

        particleLayer = make('g', {}, svg);
        cookers.forEach((cooker) => drawCooker(svg, cooker));
    }

    function drawCooker(svg, cooker) {
        const cx = cooker.cx;
        make('ellipse', { cx, cy: bowlY + 96, rx: 96, ry: 34, fill: 'url(#zkHeat)', class: 'heat-glow' }, svg);
        refs.heat[cooker.id] = svg.lastChild;
        make('path', { d: `M${cx - 102} ${bowlY + 40} L${cx + 102} ${bowlY + 40} L${cx + 88} ${bowlY + 104} L${cx - 88} ${bowlY + 104} Z`, fill: 'url(#zkSteel)', class: 'cooker-body' }, svg);
        make('ellipse', { cx, cy: bowlY, rx: 92, ry: 30, fill: 'url(#zkSteel)', class: 'cooker-body' }, svg);
        make('ellipse', { cx, cy: bowlY, rx: 80, ry: 22, fill: 'url(#zkBowl)' }, svg);
        refs.ring[cooker.id] = make('ellipse', { cx, cy: bowlY, rx: 98, ry: 36, class: 'cooker-ring' }, svg);

        const paddle = make('g', { class: 'paddle' }, svg);
        make('path', { d: `M${cx - 46} ${bowlY - 4} Q${cx} ${bowlY - 22} ${cx + 46} ${bowlY + 4}`, fill: 'none', stroke: '#e8b94a', 'stroke-width': 4, 'stroke-linecap': 'round', opacity: .7 }, paddle);
        make('rect', { x: cx - 3, y: bowlY - 24, width: 6, height: 48, rx: 3, fill: '#d4dde3', opacity: .9 }, paddle);
        refs.paddle[cooker.id] = { node: paddle, cx, cy: bowlY, angle: 0 };

        const steam = make('g', { class: 'steam' }, svg);
        for (let k = 0; k < 3; k += 1) {
            const sx = cx - 24 + k * 24;
            make('path', { d: `M${sx} ${bowlY - 8} q -8 -18 0 -34 q 8 -16 0 -30` }, steam);
        }
        refs.steam[cooker.id] = steam;

        refs.mini[cooker.id] = drawText(svg, cx - 16, bowlY + 82, '--', 'mimic-label');
    }

    function buildCookerCards() {
        const host = $('#cookerCards');
        host.innerHTML = '';
        cookers.forEach((cooker) => {
            const st = state.cookers[cooker.id];
            const card = document.createElement('article');
            card.className = 'cooker-card';
            card.id = `card-${cooker.id}`;
            card.dataset.state = 'IDLE';
            card.innerHTML = `
                <div class="card-head">
                    <strong>COOKER ${cooker.id}</strong>
                    <span class="batch-id" id="batch-${cooker.id}">#0</span>
                    <span class="state-pill" id="pill-${cooker.id}" data-state="IDLE">IDLE</span>
                </div>
                <div class="readouts">
                    <div class="readout"><small>Suhu</small><strong><span id="temp-${cooker.id}">31</span>C</strong></div>
                    <div class="readout"><small>RPM</small><strong id="rpm-${cooker.id}">0</strong></div>
                    <div class="readout"><small>Timer</small><strong id="timer-${cooker.id}">00:00</strong></div>
                </div>
                <div class="progress"><i id="progress-${cooker.id}"></i></div>
                <div class="recipe-row">
                    <span>Resep</span>
                    <select id="recipe-${cooker.id}">${recipeKeys.map((key) => `<option value="${key}">${recipes[key].name}</option>`).join('')}</select>
                </div>
                <div class="ingredient-list" id="ingredients-${cooker.id}"></div>
                <div class="card-actions">
                    <button type="button" class="start" id="start-${cooker.id}">Start</button>
                    <button type="button" id="stop-${cooker.id}">Stop</button>
                    <button type="button" class="hold" id="hold-${cooker.id}">Hold</button>
                </div>`;
            host.appendChild(card);
            $(`#recipe-${cooker.id}`).value = st.recipeKey;
            $(`#recipe-${cooker.id}`).addEventListener('change', (event) => {
                st.recipeKey = event.target.value;
                renderIngredients(cooker.id);
            });
            $(`#start-${cooker.id}`).addEventListener('click', () => startBatch(cooker.id));
            $(`#stop-${cooker.id}`).addEventListener('click', () => stopCooker(cooker.id));
            $(`#hold-${cooker.id}`).addEventListener('click', () => toggleHold(cooker.id));
            renderIngredients(cooker.id);
        });
    }

    function renderIngredients(id) {
        const st = state.cookers[id];
        const recipe = recipes[st.recipeKey];
        const host = $(`#ingredients-${id}`);
        host.innerHTML = ingredients.map((item) => {
            const amount = recipe.items[item.id] || 0;
            const done = st.doneItems[item.id] ? 'is-done' : '';
            return `<span class="ingredient-chip ${done}" data-chip="${item.id}-${id}"><i style="background:${item.color}"></i>${item.name} ${amount}${item.unit}</span>`;
        }).join('');
    }

    function buildConveyors() {
        const host = $('#conveyorGrid');
        host.innerHTML = '';
        ingredients.forEach((item) => {
            const card = document.createElement('article');
            card.className = 'conveyor-card';
            card.id = `conv-${item.id}`;
            card.innerHTML = `
                <div class="conveyor-top"><span class="swatch" style="background:${item.color}"></span><strong>${item.name}</strong><small>C-${item.id.toUpperCase()}</small></div>
                <div class="belt-meter"><i></i><span id="speed-${item.id}">0%</span></div>
                <div class="conveyor-bottom"><span id="status-${item.id}">STANDBY</span><span id="target-${item.id}">TARGET -</span></div>`;
            host.appendChild(card);
        });
    }

    function formatTimer(seconds) {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = Math.floor(seconds % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }

    function render() {
        const active = Object.values(state.cookers).filter((item) => ['DISPENSING', 'COOKING', 'HOLD'].includes(item.state)).length;
        $('#activeBatch').textContent = `${active}/2`;
        $('#outputCount').textContent = `${state.output} porsi`;
        const openAlarms = state.alarms.filter((alarm) => !alarm.ack).length;
        $('#alarmCount').textContent = openAlarms;
        $('#alarmCount').style.color = openAlarms ? 'var(--warn)' : 'var(--run)';
        $('#linePill').className = `line-pill is-${state.line.toLowerCase()}`;
        $('#lineText').textContent = state.line === 'RUN' ? 'LINE RUNNING' : state.line === 'STOP' ? 'LINE STOPPED' : 'EMERGENCY STOP';
        $('#modeTag').textContent = state.auto ? 'SIM AUTO' : 'MANUAL';
        $('#safetyState').textContent = state.estop ? 'ESTOP' : 'NORMAL';
        $('#safetyState').style.color = state.estop ? 'var(--fault)' : 'var(--run)';

        cookers.forEach((cooker) => {
            const st = state.cookers[cooker.id];
            const displayState = st.hold && st.state === 'COOKING' ? 'HOLD' : st.state;
            $(`#card-${cooker.id}`).dataset.state = displayState;
            $(`#batch-${cooker.id}`).textContent = `#${st.batch}`;
            $(`#pill-${cooker.id}`).dataset.state = displayState;
            $(`#pill-${cooker.id}`).textContent = displayState;
            $(`#temp-${cooker.id}`).textContent = Math.round(st.temp);
            $(`#rpm-${cooker.id}`).textContent = Math.round(st.rpm);
            $(`#timer-${cooker.id}`).textContent = formatTimer(st.timer);
            $(`#progress-${cooker.id}`).style.width = `${Math.round(st.progress * 100)}%`;
            $(`#start-${cooker.id}`).disabled = st.state !== 'IDLE' || state.estop;
            $(`#hold-${cooker.id}`).classList.toggle('is-active', st.hold);

            const color = { IDLE: 'var(--idle)', DISPENSING: 'var(--route)', COOKING: 'var(--cook)', HOLD: 'var(--warn)', DONE: 'var(--done)' }[displayState];
            refs.ring[cooker.id].setAttribute('stroke', color);
            refs.heat[cooker.id].setAttribute('opacity', st.state === 'COOKING' ? clamp((st.temp - 45) / 180, 0, .9) : 0);
            refs.steam[cooker.id].style.opacity = st.state === 'COOKING' ? 1 : 0;
            refs.mini[cooker.id].textContent = st.state === 'COOKING' ? `${Math.round(st.temp)}C` : st.state === 'DISPENSING' ? '..' : '--';

            const recipe = recipes[st.recipeKey];
            ingredients.forEach((item) => {
                const chip = document.querySelector(`[data-chip="${item.id}-${cooker.id}"]`);
                if (!chip) return;
                const conveyor = state.conveyors[item.id];
                chip.classList.toggle('is-done', Boolean(st.doneItems[item.id] && recipe.items[item.id]));
                chip.classList.toggle('is-active', conveyor.running && conveyor.target === cooker.id);
            });
        });

        ingredients.forEach((item) => {
            const cv = state.conveyors[item.id];
            $(`#conv-${item.id}`).classList.toggle('is-running', cv.running);
            $(`#speed-${item.id}`).textContent = `${Math.round(cv.speed)}%`;
            $(`#status-${item.id}`).textContent = cv.running ? 'FEEDING' : 'STANDBY';
            $(`#target-${item.id}`).textContent = cv.target ? `TARGET C${cv.target}` : 'TARGET -';
            cookers.forEach((cooker) => {
                const gate = refs.gate[`${item.id}-${cooker.id}`];
                gate.setAttribute('fill', cv.running && cv.target === cooker.id ? item.color : '#1b2932');
            });
        });
        cookers.forEach((cooker) => {
            const feeding = ingredients.some((item) => state.conveyors[item.id].running && state.conveyors[item.id].target === cooker.id);
            refs.chute[cooker.id].style.opacity = feeding ? .72 : 0;
        });
    }

    function renderLog() {
        const host = $('#eventLog');
        host.innerHTML = state.alarms.slice(0, 60).map((alarm) => {
            const time = alarm.time.toLocaleTimeString('id-ID', { hour12: false });
            return `<div class="log-row" data-level="${alarm.level}"><time>${time}</time><i></i><span><b>${alarm.source}</b> - ${alarm.message}</span></div>`;
        }).join('');
    }

    function log(level, source, message) {
        state.alarms.unshift({ id: ++state.alarmId, level, source, message, time: new Date(), ack: level === 'info' || level === 'ok' });
        if (state.alarms.length > 120) state.alarms.pop();
        renderLog();
        render();
    }

    function spawnParticle(itemId, cookerId) {
        if (particles.length > 120) return;
        const item = ingredients.find((entry) => entry.id === itemId);
        const lane = ingredients.findIndex((entry) => entry.id === itemId);
        const y = laneY(lane) - 2;
        const x1 = cookers.find((entry) => entry.id === cookerId).cx;
        const node = make('circle', { cx: belt.x0 + 8, cy: y, r: 4.5, fill: item.color, opacity: .95 }, particleLayer);
        particles.push({ node, x0: belt.x0 + 8, x1, y0: y, y1: bowlY - 3, phase: 'ride', elapsed: 0, rideMs: Math.abs(x1 - belt.x0) * 2.5, dropMs: 420 });
    }

    async function startBatch(id) {
        const st = state.cookers[id];
        if (st.state !== 'IDLE' || state.estop) return;
        st.abort = false;
        st.hold = false;
        st.doneItems = {};
        st.batch += 1;
        st.state = 'DISPENSING';
        st.progress = 0;
        st.temp = Math.max(31, st.temp);
        renderIngredients(id);
        const recipe = recipes[st.recipeKey];
        log('info', `COOKER ${id}`, `Batch #${st.batch} ${recipe.name} start`);

        const activeItems = ingredients.filter((item) => (recipe.items[item.id] || 0) > 0);
        for (let index = 0; index < activeItems.length; index += 1) {
            if (aborted(id)) return cleanup(id);
            const item = activeItems[index];
            await dispense(id, item.id, recipe.items[item.id]);
            st.doneItems[item.id] = true;
            st.progress = .42 * ((index + 1) / activeItems.length);
        }
        if (aborted(id)) return cleanup(id);

        st.state = 'COOKING';
        st.rpm = st.setRpm;
        st.cookTotal = recipe.cook;
        st.timer = recipe.cook;
        log('info', `COOKER ${id}`, `Cooking ${st.setRpm} rpm target 225C`);
        await cook(id);
        if (aborted(id)) return cleanup(id);

        st.state = 'DONE';
        st.rpm = 0;
        st.progress = 1;
        state.output += 1;
        log('ok', `COOKER ${id}`, `Batch #${st.batch} complete`);
        await sleep(2200);
        cleanup(id, false);
    }

    async function dispense(id, itemId, amount) {
        const cv = state.conveyors[itemId];
        cv.running = true;
        cv.target = id;
        cv.speed = clamp(55 + amount / 3, 45, 100);
        log('info', `C-${itemId.toUpperCase()}`, `Feed ${amount} -> Cooker ${id}`);
        const count = clamp(Math.round(amount / 12), 4, 9);
        for (let i = 0; i < count; i += 1) {
            if (aborted(id)) break;
            spawnParticle(itemId, id);
            await sleep(820 / count);
        }
        await sleep(620);
        cv.running = false;
        cv.target = null;
        cv.speed = 0;
    }

    function cook(id) {
        return new Promise((resolve) => {
            const st = state.cookers[id];
            const timer = window.setInterval(() => {
                if (aborted(id)) {
                    window.clearInterval(timer);
                    resolve();
                    return;
                }
                if (st.hold) return;
                st.timer = Math.max(0, st.timer - 1);
                st.temp = Math.min(225, st.temp + (225 - st.temp) * .16 + 4);
                st.progress = .42 + .58 * (1 - st.timer / st.cookTotal);
                if (st.timer <= 0) {
                    window.clearInterval(timer);
                    resolve();
                }
            }, 1000);
        });
    }

    function aborted(id) {
        return state.estop || state.line === 'STOP' || state.cookers[id].abort;
    }

    function cleanup(id, abortedBatch = true) {
        const st = state.cookers[id];
        st.state = 'IDLE';
        st.rpm = 0;
        st.timer = 0;
        st.progress = 0;
        st.hold = false;
        st.doneItems = {};
        st.abort = false;
        ingredients.forEach((item) => {
            const cv = state.conveyors[item.id];
            if (cv.target === id) {
                cv.running = false;
                cv.target = null;
                cv.speed = 0;
            }
        });
        renderIngredients(id);
        if (abortedBatch) log('warn', `COOKER ${id}`, 'Batch aborted');
        render();
    }

    function stopCooker(id) {
        const st = state.cookers[id];
        if (st.state === 'IDLE') return;
        st.abort = true;
        log('warn', `COOKER ${id}`, `Manual stop batch #${st.batch}`);
    }

    function toggleHold(id) {
        const st = state.cookers[id];
        if (st.state !== 'COOKING') return;
        st.hold = !st.hold;
        log(st.hold ? 'warn' : 'info', `COOKER ${id}`, st.hold ? 'Hold active' : 'Hold released');
        render();
    }

    function setAuto(on) {
        state.auto = Boolean(on);
        state.line = state.estop ? 'ESTOP' : state.auto ? 'RUN' : 'STOP';
        $('#autoBtn').classList.toggle('is-active', state.auto);
        $('#autoBtn').textContent = state.auto ? 'AUTO' : 'MANUAL';
        log(state.auto ? 'info' : 'warn', 'MODE', state.auto ? 'Auto simulation active' : 'Manual mode active');
        render();
    }

    function toggleEstop() {
        state.estop = !state.estop;
        if (state.estop) {
            state.line = 'ESTOP';
            Object.values(state.cookers).forEach((st) => { st.abort = true; });
            ingredients.forEach((item) => Object.assign(state.conveyors[item.id], { running: false, speed: 0, target: null }));
            $('#estopBtn').classList.add('reset');
            $('#estopBtn').textContent = 'RESET';
            log('fault', 'SAFETY', 'Emergency stop active');
        } else {
            state.line = state.auto ? 'RUN' : 'STOP';
            Object.values(state.cookers).forEach((st) => cleanup(st.id, false));
            $('#estopBtn').classList.remove('reset');
            $('#estopBtn').textContent = 'E-STOP';
            log('ok', 'SAFETY', 'Emergency stop reset');
        }
        render();
    }

    function simStep() {
        if (!state.auto || state.estop) return;
        const idle = cookers.map((cooker) => cooker.id).filter((id) => state.cookers[id].state === 'IDLE');
        if (!idle.length) return;
        const id = idle[Math.floor(Math.random() * idle.length)];
        const recipe = recipeKeys[Math.floor(Math.random() * recipeKeys.length)];
        state.cookers[id].recipeKey = recipe;
        $(`#recipe-${id}`).value = recipe;
        renderIngredients(id);
        startBatch(id);
    }

    let previous = performance.now();
    function loop(now) {
        const dt = Math.min(60, now - previous);
        previous = now;
        ingredients.forEach((item) => {
            const cv = state.conveyors[item.id];
            const ref = refs.tread[item.id];
            if (cv.running) {
                ref.offset = (ref.offset - (cv.speed / 100) * 90 * dt / 1000) % belt.tread;
                ref.node.setAttribute('transform', `translate(${ref.offset},0)`);
            }
        });
        cookers.forEach((cooker) => {
            const st = state.cookers[cooker.id];
            const ref = refs.paddle[cooker.id];
            if (st.rpm > 0 && !st.hold) {
                ref.angle = (ref.angle + st.rpm * 6 * dt / 1000) % 360;
                ref.node.setAttribute('transform', `rotate(${ref.angle} ${ref.cx} ${ref.cy})`);
            }
        });
        for (let i = particles.length - 1; i >= 0; i -= 1) {
            const particle = particles[i];
            particle.elapsed += dt;
            if (particle.phase === 'ride') {
                const k = Math.min(1, particle.elapsed / particle.rideMs);
                particle.node.setAttribute('cx', particle.x0 + (particle.x1 - particle.x0) * k);
                if (k >= 1) {
                    particle.phase = 'drop';
                    particle.elapsed = 0;
                }
            } else {
                const k = Math.min(1, particle.elapsed / particle.dropMs);
                particle.node.setAttribute('cy', particle.y0 + (particle.y1 - particle.y0) * k);
                particle.node.setAttribute('opacity', .95 - .88 * k);
                if (k >= 1) {
                    particle.node.remove();
                    particles.splice(i, 1);
                }
            }
        }
        requestAnimationFrame(loop);
    }

    function tick() {
        Object.values(state.cookers).forEach((st) => {
            if (st.state !== 'COOKING' && st.temp > 31) st.temp = Math.max(31, st.temp - 1.2);
        });
        $('#clock').textContent = `${new Date().toLocaleTimeString('id-ID', { hour12: false })} ${new Date().toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })}`;
        render();
    }

    const kualiApi = {
        getState: () => JSON.parse(JSON.stringify(state)),
        setAuto,
        estop: toggleEstop,
        startBatch,
        stop: stopCooker,
        update(payload = {}) {
            if (payload.line) state.line = payload.line;
            if (payload.cookers) Object.entries(payload.cookers).forEach(([id, patch]) => Object.assign(state.cookers[id], patch));
            if (payload.conveyors) Object.entries(payload.conveyors).forEach(([id, patch]) => Object.assign(state.conveyors[id], patch));
            render();
        },
        alarm: ({ level = 'info', source = 'EXT', message = '' } = {}) => log(level, source, message),
    };

    window.KualiHMI = kualiApi;

    buildMimic();
    buildCookerCards();
    buildConveyors();
    log('ok', 'SYSTEM', 'Kuali online');
    render();
    requestAnimationFrame(loop);
    window.setInterval(tick, 250);
    window.setInterval(simStep, 3600);
    window.setTimeout(simStep, 600);

    $('#autoBtn').addEventListener('click', () => setAuto(!state.auto));
    $('#estopBtn').addEventListener('click', toggleEstop);
    $('#ackBtn').addEventListener('click', () => {
        state.alarms.forEach((alarm) => { alarm.ack = true; });
        renderLog();
        render();
    });
})();
