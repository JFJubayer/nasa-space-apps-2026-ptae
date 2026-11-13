/* PTAE app: ranking, map, evidence panel and method page driven by global_results.json. */
(function () {
    'use strict';

    const FLOOR = 0.02;
    const DIMS = [
        { key: 'terrain', label: 'Terrain', kind: 'measured' },
        { key: 'environment', label: 'Environment', kind: 'measured' },
        { key: 'geology', label: 'Geology', kind: 'curated' },
    ];
    const PRESETS = {
        balanced: { label: 'Balanced', terrain: 50, environment: 25, geology: 25 },
        rover: { label: 'Rover traverse', terrain: 70, environment: 15, geology: 15 },
        habitat: { label: 'Habitat', terrain: 25, environment: 50, geology: 25 },
        resources: { label: 'Science and resources', terrain: 20, environment: 20, geology: 60 },
    };
    const CATEGORY_LABEL = { benchmark: 'benchmark', emerging: 'less-studied', control: 'control' };
    const BODY_COLOR = { mars: '#d9825b', moon: '#9db4c8' };
    const RAMP_LOW = [59, 67, 80];
    const RAMP_HIGH = [227, 168, 74];

    const state = {
        data: null, body: 'mars', view: 'all', preset: 'balanced', agg: 'geometric', show: 'all', selected: null,
        weights: { terrain: 50, environment: 25, geology: 25 }, map: null, markers: null, windowLayer: null, chart: null,
        rows: [],
    };

    const $ = id => document.getElementById(id);
    const el = (tag, attrs = {}, children = []) => {
        const node = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'class') node.className = value;
            else if (key === 'text') node.textContent = value;
            else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
            else node.setAttribute(key, value);
        }
        for (const child of [].concat(children)) if (child !== null && child !== undefined && child !== false) node.append(child);
        return node;
    };
    const mean = values => values.reduce((a, b) => a + b, 0) / values.length;
    const shortName = name => name.split(/ \(|, /)[0];
    const siteById = id => state.data.sites.find(s => s.id === id);
    const targetsOf = body => state.data.targets.filter(t => t.body === body);

    function aci(dims, weights = state.weights, mode = state.agg) {
        const total = weights.terrain + weights.environment + weights.geology;
        if (total <= 0) return 0;
        if (mode === 'additive') return DIMS.reduce((sum, d) => sum + weights[d.key] * dims[d.key], 0) / total;
        const logSum = DIMS.reduce((sum, d) => sum + weights[d.key] * Math.log(Math.max(dims[d.key] / 100, FLOOR)), 0);
        return 100 * Math.exp(logSum / total);
    }

    /* ---------- Data shaping ---------- */
    function currentTargets() {
        return state.view === 'all' ? targetsOf(state.body) : state.data.targets.filter(t => t.id === state.view);
    }

    function viewLabel() {
        if (state.view === 'all') return `all ${targetsOf(state.body).length} ${state.body === 'mars' ? 'Mars' : 'lunar'} targets`;
        return state.data.targets.find(t => t.id === state.view).name;
    }

    function buildRows() {
        const targets = currentTargets();
        const entries = new Map();
        for (const target of targets) {
            for (const r of target.rankings) {
                if (!entries.has(r.site_id)) entries.set(r.site_id, []);
                entries.get(r.site_id).push({ target, r, score: aci(r) });
            }
        }
        const rows = state.data.sites.map(site => {
            const list = entries.get(site.id);
            const best = list.reduce((a, b) => (b.score > a.score ? b : a));
            return {
                site, entries: list, best,
                score: mean(list.map(e => e.score)),
                terrain: mean(list.map(e => e.r.terrain)),
                environment: mean(list.map(e => e.r.environment)),
                geology: mean(list.map(e => e.r.geology)),
            };
        }).sort((a, b) => b.score - a.score);
        rows.forEach((row, index) => { row.rank = index + 1; });
        state.rows = rows;
    }

    const visibleRows = () => state.rows.filter(row => state.show === 'all' || row.site.category === state.show);

    function strengthOf(score) {
        const scores = state.rows.filter(r => r.site.category !== 'control').map(r => r.score);
        const low = Math.min(...scores);
        const high = Math.max(...scores);
        return high > low ? Math.max(0, Math.min(1, (score - low) / (high - low))) : 0.5;
    }

    function colorFor(score) {
        const t = strengthOf(score);
        return `rgb(${RAMP_LOW.map((c, i) => Math.round(c + (RAMP_HIGH[i] - c) * t)).join(',')})`;
    }

    /* ---------- Intro and finding ---------- */
    function renderFinding() {
        const { body_summary: summary, validation } = state.data;
        const top5 = summary.mars.rankings.slice(0, 5);
        const emerging = top5.filter(r => r.category === 'emerging');
        const moonAuc = mean(validation.per_target.filter(r => /shackleton|malapert/.test(r.target_id)).map(r => r.auc_aci));
        const marsNames = emerging.map(r => shortName(siteById(r.site_id).name)).join(', ');
        $('finding').replaceChildren(
            el('span', { class: 'label', text: 'What the data says' }),
            el('span', {}, [el('strong', { text: 'Mars. ' }), document.createTextNode(`${emerging.length} of the 5 best-matching regions are less-studied: ${marsNames}.`)]),
            el('span', {}, [el('strong', { text: 'Moon. ' }), document.createTextNode(`Weaker evidence. Steep mountains also match lunar polar terrain (separation from controls, AUC ${moonAuc.toFixed(2)}), so treat these as hypotheses.`)]),
        );
    }

    /* ---------- Controls ---------- */
    function populateTargets() {
        const select = $('target');
        const targets = targetsOf(state.body);
        select.replaceChildren(
            el('option', { value: 'all', text: `All ${targets.length} ${state.body === 'mars' ? 'Mars' : 'lunar'} targets (mean)` }),
            ...targets.map(t => el('option', { value: t.id, text: t.name })),
        );
        select.value = state.view;
    }

    function buildControls() {
        document.querySelectorAll('#body-seg button').forEach(button => button.addEventListener('click', () => {
            state.body = button.dataset.body;
            state.view = 'all';
            state.selected = null;
            refresh();
        }));
        $('target').addEventListener('change', event => { state.view = event.target.value; refresh(); });
        $('show').addEventListener('change', event => { state.show = event.target.value; refresh(); });
        $('agg').addEventListener('change', event => { state.agg = event.target.value; refresh(); });
        $('adv-toggle').addEventListener('click', event => {
            const open = event.currentTarget.getAttribute('aria-expanded') !== 'true';
            event.currentTarget.setAttribute('aria-expanded', String(open));
            $('adv').hidden = !open;
        });
        for (const dim of DIMS) {
            $(`w-${dim.key}`).addEventListener('input', event => {
                state.weights[dim.key] = Number(event.target.value);
                state.preset = matchPreset();
                refresh();
            });
        }
        $('presets').replaceChildren(...Object.entries(PRESETS).map(([key, preset]) => el('button', {
            type: 'button', 'data-preset': key, 'aria-pressed': 'false', text: preset.label,
            onclick: () => { state.weights = { terrain: preset.terrain, environment: preset.environment, geology: preset.geology }; state.preset = key; refresh(); },
        })));
    }

    function matchPreset() {
        const found = Object.entries(PRESETS).find(([, p]) => DIMS.every(d => p[d.key] === state.weights[d.key]));
        return found ? found[0] : 'custom';
    }

    function syncControls() {
        document.querySelectorAll('#body-seg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.body === state.body)));
        document.querySelectorAll('#presets button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.preset === state.preset)));
        for (const dim of DIMS) { $(`w-${dim.key}`).value = state.weights[dim.key]; $(`o-${dim.key}`).textContent = state.weights[dim.key]; }
        $('show').value = state.show;
        $('agg').value = state.agg;
        populateTargets();
    }

    /* ---------- List ---------- */
    function microBars(row) {
        return el('span', { class: 'micro', title: `Terrain ${row.terrain.toFixed(0)}, environment ${row.environment.toFixed(0)}, geology ${row.geology.toFixed(0)}` },
            DIMS.map(d => el('i', { style: `--h:${Math.max(row[d.key], 3)}%` })));
    }

    function renderList() {
        const rows = visibleRows();
        $('list-title').textContent = state.view === 'all' ? `Mean over ${viewLabel()}` : shortName(viewLabel());
        $('list-count').textContent = `${rows.length} of ${state.rows.length}`;
        const list = $('rows');
        if (!rows.length) { list.replaceChildren(el('li', { class: 'empty', text: 'No regions match this filter.' })); return; }
        list.replaceChildren(...rows.map(row => {
            const current = row.site.id === state.selected;
            return el('li', {}, [el('button', {
                type: 'button', class: 'row', 'data-site': row.site.id, 'aria-current': String(current),
                'aria-label': `${row.rank}. ${row.site.name}, ACI ${row.score.toFixed(1)}`,
                onclick: () => select(row.site.id, { fly: true }),
            }, [
                el('span', { class: 'rank num', text: String(row.rank) }),
                el('span', {}, [
                    el('div', { class: 'row-name', text: row.site.name }),
                    el('div', { class: 'row-meta' }, [el('span', { class: `tag ${row.site.category}`, text: CATEGORY_LABEL[row.site.category] }), el('span', { class: 'where', text: row.site.country })]),
                ]),
                el('span', {}, [el('div', { class: 'score num', text: row.score.toFixed(1) }), microBars(row)]),
            ])]);
        }));
    }

    /* ---------- Map ---------- */
    function initMap() {
        if (state.map || typeof L === 'undefined') return;
        state.map = L.map('map', { worldCopyJump: true, minZoom: 2, zoomSnap: 0.5, attributionControl: true }).setView([22, 15], 2);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 12, attribution: 'Tiles &copy; Esri, HERE, Garmin, OpenStreetMap contributors',
        }).addTo(state.map);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', { maxZoom: 12, opacity: 0.85 }).addTo(state.map);
        state.markers = L.layerGroup().addTo(state.map);
        state.windowLayer = L.layerGroup().addTo(state.map);
        new ResizeObserver(() => state.map.invalidateSize()).observe($('map'));
    }

    function renderMap() {
        if (!state.map) return;
        state.markers.clearLayers();
        for (const row of visibleRows()) {
            const control = row.site.category === 'control';
            const selected = row.site.id === state.selected;
            const strength = strengthOf(row.score);
            const marker = L.circleMarker([row.site.lat, row.site.lon], {
                radius: (selected ? 10 : 6) + 6 * strength,
                color: selected ? '#ffffff' : (control ? '#8a9098' : '#0f1113'),
                weight: selected ? 2.5 : (control ? 1.5 : 1),
                dashArray: control && !selected ? '3 3' : null,
                fillColor: control ? '#8a9098' : colorFor(row.score),
                fillOpacity: control ? 0.18 : 0.95,
            });
            marker.bindTooltip(`${row.site.name}: ${row.score.toFixed(1)}`, { direction: 'top' });
            marker.on('click', () => select(row.site.id, { fly: false }));
            marker.addTo(state.markers);
        }
        drawWindow();
    }

    function drawWindow() {
        if (!state.map) return;
        state.windowLayer.clearLayers();
        const row = state.rows.find(r => r.site.id === state.selected);
        if (!row) return;
        const { lat, lon } = row.best.r.best_window;
        const half = state.data.method.window_km / 2;
        const dLat = half / 111.32;
        const dLon = half / (111.32 * Math.max(Math.cos(lat * Math.PI / 180), 0.05));
        L.rectangle([[lat - dLat, lon - dLon], [lat + dLat, lon + dLon]], { color: '#e3a84a', weight: 2, fill: false }).addTo(state.windowLayer);
    }

    /* ---------- Detail ---------- */
    function select(siteId, { fly }) {
        state.selected = siteId;
        renderList();
        renderMap();
        renderDetail();
        writeHash();
        const row = state.rows.find(r => r.site.id === siteId);
        if (fly && state.map && row) {
            const { lat, lon } = row.best.r.best_window;
            state.map.flyTo([lat, lon], Math.max(state.map.getZoom(), 5), { duration: 0.7 });
        }
        document.querySelector(`#rows [data-site="${CSS.escape(siteId)}"]`)?.scrollIntoView({ block: 'nearest' });
        if (window.matchMedia('(max-width: 1180px)').matches) $('detail').scrollIntoView({ block: 'start' });
    }

    function sharedTags(site, target) {
        return Object.entries(target.tags)
            .filter(([tag, weight]) => weight > 0 && (site.tags[tag] || 0) >= 0.5)
            .map(([tag]) => state.data.tag_vocabulary[tag] || tag);
    }

    function section(title, ...children) {
        return el('section', { class: 'section' }, [el('h3', { text: title }), ...children]);
    }

    function renderDetail() {
        const panel = $('detail');
        const row = state.rows.find(r => r.site.id === state.selected);
        if (!row) { panel.replaceChildren(el('div', { class: 'empty', text: 'Select a region from the list or the map.' })); return; }
        const { site, best } = row;
        const target = best.target;
        const gaps = state.data.irreducible_gaps;
        const aggregate = state.view === 'all';
        const sharedNames = sharedTags(site, target);
        const robust = best.r.robust;
        const scores = row.entries.map(e => e.score);

        const nodes = [];
        nodes.push(el('div', {}, [
            el('h2', { text: site.name }),
            el('div', { class: 'sub' }, [el('span', { class: `tag ${site.category}`, text: CATEGORY_LABEL[site.category] }), el('span', { text: `${site.country}. Rank ${row.rank} of ${state.rows.length}.` })]),
        ]));
        nodes.push(el('div', { class: 'bigscore' }, [
            el('span', { class: 'num', text: row.score.toFixed(1) }),
            el('span', { text: aggregate ? `mean ACI over ${scores.length} targets (${Math.min(...scores).toFixed(0)} to ${Math.max(...scores).toFixed(0)})` : 'ACI for this target' }),
        ]));
        nodes.push(section('Similarity by dimension', ...DIMS.map(d => el('div', { class: 'dim' }, [
            el('span', { class: 'name' }, [d.label, el('small', { text: d.kind })]),
            el('div', { class: 'bar' }, [el('i', { style: `width:${row[d.key]}%` })]),
            el('span', { class: 'num', text: row[d.key].toFixed(0) }),
        ]))));

        const holds = el('div', { class: 'holds' }, [el('p', { text: site.heritage })]);
        if (sharedNames.length) holds.append(el('div', { class: 'chips' }, sharedNames.map(name => el('span', { class: 'chip', text: name }))));
        else holds.append(el('p', { class: 'hint', text: 'No curated geology tags in common with this target.' }));
        nodes.push(section('Where it matches', holds));

        const gapItems = best.r.gaps.length ? best.r.gaps : ['No single measured gap is large.'];
        const bodyGaps = gaps[target.body];
        nodes.push(section('Where it breaks down', el('div', { class: 'breaks' }, [el('ul', {}, [
            ...gapItems.map(text => el('li', { text })),
            el('li', { text: site.limits }),
            el('li', { text: `Not reproducible on Earth: gravity ${gaps.earth.gravity_ms2} vs ${bodyGaps.gravity_ms2} m/s2, pressure ${gaps.earth.surface_pressure_kpa} vs ${bodyGaps.surface_pressure_kpa} kPa, radiation ${gaps.earth.surface_radiation_msv_per_day} vs ${bodyGaps.surface_radiation_msv_per_day} mSv/day.` }),
        ])])));

        const chartBox = el('div', { class: 'chart-box' }, [el('canvas', { id: 'slope-chart', role: 'img', 'aria-label': `Slope against baseline length for ${site.name} and ${target.name}` })]);
        nodes.push(section(`Terrain profile${aggregate ? ` against ${shortName(target.name)}` : ''}`, chartBox,
            el('p', { class: 'hint', text: 'Median slope rises or falls with baseline length. Close lines mean similar roughness at every scale.' })));

        const w = best.r.best_window;
        nodes.push(section('Best 40 km window', el('div', { class: 'kv' }, [
            el('span', {}, [el('strong', { class: 'num', text: `${w.lat.toFixed(3)}, ${w.lon.toFixed(3)}` }), document.createTextNode(' '),
                el('a', { href: `https://www.openstreetmap.org/?mlat=${w.lat}&mlon=${w.lon}#map=9/${w.lat}/${w.lon}`, target: '_blank', rel: 'noopener noreferrer', text: 'open map' })]),
            el('span', { text: `${best.r.coverage.toFixed(0)}% of the region's ${best.r.n_windows} windows are above 50% terrain similarity.` }),
            el('span', { text: `Across 1000 random weightings the rank is ${robust.rank_p10} to ${robust.rank_p90} (median ${robust.rank_median}); top 3 in ${(robust.prob_top3 * 100).toFixed(0)}% of draws.` }),
        ])));

        const c = site.climate;
        const facts = [['Mean temperature', `${c.t_mean_c.toFixed(1)} C`], ['Daily range', `${c.t_daily_range_c.toFixed(1)} C`], ['Precipitation', `${c.precip_mm_yr.toFixed(0)} mm/yr`],
            ['Humidity', `${c.rel_humidity_pct.toFixed(0)} %`], ['Air pressure', `${c.surface_pressure_kpa.toFixed(0)} kPa`], ['Terrain windows', String(best.r.n_windows)]];
        nodes.push(section('Climate (NASA POWER)', el('dl', { class: 'facts' }, facts.map(([k, v]) => el('div', {}, [el('dt', { text: k }), el('dd', { text: v })])))));

        if (aggregate) {
            const table = el('table', { class: 'pt-table' }, [el('tbody', {}, row.entries.slice().sort((a, b) => b.score - a.score).map(e => el('tr', {}, [
                el('td', { text: e.target.name }), el('td', { class: 'num', text: `${e.score.toFixed(1)} (#${state.rows.length ? rankIn(e.target, site.id) : ''})` }),
            ])))]);
            nodes.push(section('By target', table));
        }

        panel.replaceChildren(el('div', { class: 'detail' }, nodes));
        panel.scrollTop = 0;
        drawChart(best.r, target);
    }

    function rankIn(target, siteId) {
        const ordered = target.rankings.map(r => ({ id: r.site_id, score: aci(r) })).sort((a, b) => b.score - a.score);
        return ordered.findIndex(r => r.id === siteId) + 1;
    }

    function drawChart(r, target) {
        const canvas = $('slope-chart');
        if (!canvas || typeof Chart === 'undefined') return;
        if (state.chart) state.chart.destroy();
        const valid = new Set(target.valid_baselines_m);
        const targetValues = target.slope_profile.baselines_m.map((b, i) => (valid.has(b) ? target.slope_profile.median_deg[i] : null));
        const line = (label, data, color, dash) => ({ label, data, borderColor: color, backgroundColor: color, borderDash: dash || [], borderWidth: 2, pointRadius: 3, tension: 0.15 });
        state.chart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: r.slope_profile.baselines_m.map(b => (b >= 1000 ? `${b / 1000} km` : `${b} m`)),
                datasets: [
                    line(shortName(target.name), targetValues, BODY_COLOR[target.body]),
                    line('Earth median', r.slope_profile.median_deg, '#e3a84a'),
                    line('Earth 90th pct', r.slope_profile.p90_deg, '#e3a84a', [4, 4]),
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false, animation: false,
                plugins: { legend: { position: 'bottom', labels: { color: '#a0a5ab', boxWidth: 10, boxHeight: 2, font: { size: 11 } } } },
                scales: {
                    x: { ticks: { color: '#737a82', font: { size: 11 } }, grid: { color: '#22272c' } },
                    y: { type: 'logarithmic', title: { display: true, text: 'slope (degrees)', color: '#737a82', font: { size: 11 } }, ticks: { color: '#737a82', font: { size: 11 } }, grid: { color: '#22272c' } },
                },
            },
        });
    }

    /* ---------- Method page ---------- */
    function renderMethod() {
        const { validation, method, irreducible_gaps: gaps, references } = state.data;
        const marsAuc = mean(validation.per_target.filter(r => !/shackleton|malapert/.test(r.target_id)).map(r => r.auc_aci));
        const moonAuc = mean(validation.per_target.filter(r => /shackleton|malapert/.test(r.target_id)).map(r => r.auc_aci));
        $('trust-callout').textContent = `${validation.control_sites.length} deliberate negative controls (plains, rainforest, glaciated and monsoon mountains) rank below real candidates ${(marsAuc * 100).toFixed(0)}% of the time for Mars targets and ${(moonAuc * 100).toFixed(0)}% for lunar targets (AUC ${marsAuc.toFixed(2)} and ${moonAuc.toFixed(2)}; 50% would be chance).`;
        $('trust-list').replaceChildren(...[
            `Terrain alone separates controls from candidates at AUC ${validation.mean_auc_terrain.toFixed(2)}, climate alone at ${validation.mean_auc_environment.toFixed(2)}, geology alone at ${validation.mean_auc_geology.toFixed(2)}. The dimensions complement each other.`,
            'The lunar polar region is rugged, so steep mountain controls match its slope statistics. Only climate and geology reject them, which is why Moon results are weaker.',
            'We first combined dimensions by addition. That let a wet alpine valley rank first for the Moon, so we switched to the geometric mean. Both are available; the change does not remove the Moon weakness.',
            `Mars elevation is gridded MOLA (463 m), so only baselines of ${method.mars_min_valid_baseline_m} m and longer are compared for Mars. Rover-scale roughness needs HiRISE or CTX data.`,
            'NASA POWER is a 0.5 degree reanalysis and is coarse for single sites. Geology tags and the "less-studied" label are judgement, not measurements.',
            'The ranking is a screening tool for deciding where to look next. It does not confirm any site as an analog.',
        ].map(text => el('li', { text })));
        const rowsData = [
            ['Gravity (m/s2)', gaps.earth.gravity_ms2, gaps.moon.gravity_ms2, gaps.mars.gravity_ms2],
            ['Surface pressure (kPa)', gaps.earth.surface_pressure_kpa, gaps.moon.surface_pressure_kpa, gaps.mars.surface_pressure_kpa],
            ['Surface radiation (mSv/day)', gaps.earth.surface_radiation_msv_per_day, gaps.moon.surface_radiation_msv_per_day, gaps.mars.surface_radiation_msv_per_day],
        ];
        $('gap-body').replaceChildren(...rowsData.map(cells => el('tr', {}, cells.map((c, i) => el('td', { class: i ? 'num' : '', text: String(c) })))));
        $('gap-note').textContent = `${gaps.note} Moon: ${gaps.moon.other} Mars: ${gaps.mars.other}`;
        $('data-list').replaceChildren(...Object.values(method.data).map(text => el('li', { text })));
        $('ref-list').replaceChildren(...references.map(text => el('li', { text })));
    }

    /* ---------- Routing and URL state ---------- */
    function writeHash() {
        if (location.hash === '#method') return;
        const params = new URLSearchParams();
        if (state.body !== 'mars') params.set('b', state.body);
        if (state.view !== 'all') params.set('t', state.view);
        if (state.selected) params.set('s', state.selected);
        if (state.preset !== 'balanced') params.set('p', state.preset === 'custom' ? `${state.weights.terrain}-${state.weights.environment}-${state.weights.geology}` : state.preset);
        if (state.agg !== 'geometric') params.set('g', state.agg);
        if (state.show !== 'all') params.set('f', state.show);
        const text = params.toString();
        history.replaceState(null, '', text ? `#${text}` : location.pathname + location.search);
    }

    function readHash() {
        const params = new URLSearchParams(location.hash.slice(1));
        const body = params.get('b');
        if (body === 'moon' || body === 'mars') state.body = body;
        const view = params.get('t');
        state.view = view && state.data.targets.some(t => t.id === view && t.body === state.body) ? view : 'all';
        const site = params.get('s');
        state.selected = site && state.data.sites.some(s => s.id === site) ? site : null;
        const p = params.get('p');
        if (p && PRESETS[p]) { state.preset = p; state.weights = { terrain: PRESETS[p].terrain, environment: PRESETS[p].environment, geology: PRESETS[p].geology }; }
        else if (p && /^\d+-\d+-\d+$/.test(p)) { const [t, e, g] = p.split('-').map(Number); state.weights = { terrain: t, environment: e, geology: g }; state.preset = matchPreset(); }
        if (params.get('g') === 'additive') state.agg = 'additive';
        const f = params.get('f');
        if (['emerging', 'benchmark', 'control'].includes(f)) state.show = f;
    }

    function route() {
        const method = location.hash === '#method';
        $('view-tool').hidden = method;
        $('view-method').hidden = !method;
        $('nav-tool').toggleAttribute('aria-current', !method);
        if (!method) $('nav-tool').setAttribute('aria-current', 'page');
        $('nav-method').toggleAttribute('aria-current', method);
        if (method) $('nav-method').setAttribute('aria-current', 'page');
        if (method) window.scrollTo({ top: 0 });
        else if (state.map) setTimeout(() => state.map.invalidateSize(), 50);
    }

    function refresh() {
        buildRows();
        if (state.selected && !state.rows.some(r => r.site.id === state.selected)) state.selected = null;
        syncControls();
        renderList();
        renderMap();
        renderDetail();
        writeHash();
    }

    async function init() {
        try {
            const response = await fetch('global_results.json', { cache: 'no-store' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            state.data = await response.json();
        } catch (error) {
            document.querySelector('#view-tool .intro').after(el('div', { class: 'error', role: 'alert', text: 'Results could not be loaded (global_results.json). From the repository root run: python -m src.global_search' }));
            return;
        }
        readHash();
        buildControls();
        renderFinding();
        renderMethod();
        initMap();
        refresh();
        if (state.selected) {
            const row = state.rows.find(r => r.site.id === state.selected);
            state.map?.setView([row.best.r.best_window.lat, row.best.r.best_window.lon], 5);
        }
        $('rows').addEventListener('keydown', event => {
            if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
            const buttons = [...document.querySelectorAll('#rows .row')];
            const index = buttons.indexOf(document.activeElement);
            if (index < 0) return;
            event.preventDefault();
            buttons[Math.max(0, Math.min(buttons.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)))].focus();
        });
        window.addEventListener('hashchange', () => { if (location.hash !== '#method') { readHash(); refresh(); } route(); });
        route();
    }

    window.addEventListener('load', init);
})();
