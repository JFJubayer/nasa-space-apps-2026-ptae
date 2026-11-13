/* PTAE global analog search tab: ranking, map, per-site evidence and honesty panels from global_results.json. */
(function () {
    'use strict';

    const FLOOR = 0.02;
    const DIMENSIONS = [
        { key: 'terrain', label: 'Terrain', note: 'Measured: multi-baseline slope statistics from real DEMs' },
        { key: 'environment', label: 'Environment', note: 'Measured: NASA POWER climate vs Earth-achievable target' },
        { key: 'geology', label: 'Geology', note: 'Curated expert priors (not measured)' },
    ];
    const PRESETS = {
        balanced: { terrain: 50, environment: 25, geology: 25, label: 'Balanced' },
        rover: { terrain: 70, environment: 15, geology: 15, label: 'Rover traverse' },
        habitat: { terrain: 25, environment: 50, geology: 25, label: 'Habitat and operations' },
        isru: { terrain: 20, environment: 20, geology: 60, label: 'Science and resources' },
    };
    const FEATURE_NAMES = {
        t_mean_c: 'Mean temperature', t_daily_range_c: 'Daily range', precip_mm_yr: 'Precipitation',
        rel_humidity_pct: 'Humidity', surface_pressure_kpa: 'Air pressure',
    };

    const state = {
        data: null, targetId: null, weights: { ...PRESETS.balanced }, aggregation: 'geometric',
        category: 'all', selectedSite: null, map: null, markerLayer: null, windowLayer: null, chart: null,
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
        for (const child of [].concat(children)) if (child) node.append(child);
        return node;
    };

    function aci(row, weights = state.weights, mode = state.aggregation) {
        const scores = { terrain: row.terrain / 100, environment: row.environment / 100, geology: row.geology / 100 };
        const total = weights.terrain + weights.environment + weights.geology;
        if (total <= 0) return 0;
        if (mode === 'additive') {
            return 100 * DIMENSIONS.reduce((sum, d) => sum + weights[d.key] * scores[d.key], 0) / total;
        }
        const logSum = DIMENSIONS.reduce((sum, d) => sum + weights[d.key] * Math.log(Math.max(scores[d.key], FLOOR)), 0);
        return 100 * Math.exp(logSum / total);
    }

    const siteById = id => state.data.sites.find(site => site.id === id);
    const currentTarget = () => state.data.targets.find(t => t.id === state.targetId);

    function rankedRows() {
        const target = currentTarget();
        const rows = target.rankings
            .map(row => ({ ...row, score: aci(row) }))
            .sort((a, b) => b.score - a.score);
        rows.forEach((row, index) => { row.liveRank = index + 1; });
        return rows;
    }

    function colorFor(score, category) {
        if (category === 'control') return '#8493a3';
        const t = Math.max(0, Math.min(1, score / 70));
        const r = Math.round(58 + (255 - 58) * t);
        const g = Math.round(143 + (215 - 143) * t);
        const b = Math.round(192 + (131 - 192) * t);
        return `rgb(${r},${g},${b})`;
    }

    function categoryPill(category) {
        const label = { benchmark: 'Benchmark', emerging: 'Emerging', control: 'Control' }[category] || category;
        return el('span', { class: `gs-pill ${category}`, text: label });
    }

    /* ---------- Summary cards ---------- */
    function renderSummary() {
        const { body_summary: summary, validation } = state.data;
        const moon = summary.moon.rankings[0];
        const mars = summary.mars.rankings[0];
        const named = row => siteById(row.site_id).name;
        const emergingTop = ['moon', 'mars'].flatMap(body =>
            summary[body].rankings.slice(0, 5).filter(row => row.category === 'emerging').map(row => ({ body, row })));
        const marsAuc = mean(validation.per_target.filter(r => r.target_id.match(/jezero|gale|gusev|meridiani|oxia|hellas/)).map(r => r.auc_aci));
        const moonAuc = mean(validation.per_target.filter(r => r.target_id.match(/shackleton|malapert/)).map(r => r.auc_aci));
        const nSites = state.data.sites.length;
        const nWindows = state.data.sites.reduce((sum, s) => sum + s.n_windows, 0);

        const cards = [
            ['Best Moon analog (mean of 2 polar targets)', named(moon), `${moon.mean_aci.toFixed(1)} ACI, ${moon.category}`],
            ['Best Mars analog (mean of 6 targets)', named(mars), `${mars.mean_aci.toFixed(1)} ACI, ${mars.category}`],
            ['Less-studied sites in the top 5',
                `${emergingTop.length} of 10 slots`,
                emergingTop.map(({ body, row }) => `${named(row)} (${body})`).join('; ') || 'none'],
            ['Control separation (AUC)', `Mars ${marsAuc.toFixed(2)} / Moon ${moonAuc.toFixed(2)}`,
                `Chance that a real analog candidate outranks a negative control. ${nSites} regions, ${nWindows} terrain windows.`],
        ];
        const grid = $('gs-stat-grid');
        grid.replaceChildren(...cards.map(([title, value, note]) =>
            el('article', { class: 'gs-stat' }, [el('h3', { text: title }), el('strong', { text: value }), el('span', { text: note })])));
    }

    const mean = values => values.length ? values.reduce((a, b) => a + b, 0) / values.length : NaN;

    function renderHome() {
        const { body_summary: summary, validation } = state.data;
        for (const body of ['moon', 'mars']) {
            const top = summary[body].rankings[0];
            const site = siteById(top.site_id);
            const set = (id, text) => { const node = $(id); if (node) { node.classList.remove('json-loading-skeleton'); node.textContent = text; } };
            set(`takeaway-${body}-site`, site.name);
            set(`takeaway-${body}-score`, `${top.mean_aci.toFixed(1)} mean ACI`);
            set(`takeaway-${body}-breakdown`, `${top.category === 'emerging' ? 'Less-studied region' : 'Established analog'}; ranges ${top.min_aci.toFixed(0)}-${top.max_aci.toFixed(0)} across targets`);
        }
        const verdict = $('takeaway-validation');
        if (verdict) {
            verdict.classList.remove('json-loading-skeleton');
            verdict.textContent = `Real DEMs and NASA climate for ${state.data.sites.length} regions. Candidates beat negative controls ${(validation.mean_auc_aci * 100).toFixed(0)}% of the time on average (terrain alone: ${(validation.mean_auc_terrain * 100).toFixed(0)}%).`;
        }
    }

    /* ---------- Controls ---------- */
    function buildControls() {
        const select = $('gs-target');
        select.replaceChildren(...state.data.targets.map(t =>
            el('option', { value: t.id, text: `${t.body === 'moon' ? 'Moon' : 'Mars'}: ${t.name}` })));
        select.value = state.targetId;
        select.addEventListener('change', () => { state.targetId = select.value; state.selectedSite = null; refresh(); });

        $('gs-category').addEventListener('change', event => { state.category = event.target.value; refresh(); });
        $('gs-aggregation').addEventListener('change', event => { state.aggregation = event.target.value; refresh(); });

        for (const dim of DIMENSIONS) {
            const input = $(`gs-w-${dim.key}`);
            input.addEventListener('input', () => {
                state.weights[dim.key] = Number(input.value);
                syncSliders();
                refresh();
            });
        }
        const row = $('gs-presets');
        row.replaceChildren(...Object.entries(PRESETS).map(([key, preset]) =>
            el('button', {
                type: 'button', class: 'gs-btn', 'data-preset': key, 'aria-pressed': key === 'balanced' ? 'true' : 'false', text: preset.label,
                onclick: () => {
                    Object.assign(state.weights, { terrain: preset.terrain, environment: preset.environment, geology: preset.geology });
                    syncSliders(key);
                    refresh();
                },
            })));
        syncSliders('balanced');
    }

    function syncSliders(activePreset = null) {
        for (const dim of DIMENSIONS) {
            $(`gs-w-${dim.key}`).value = state.weights[dim.key];
            $(`gs-w-${dim.key}-out`).textContent = state.weights[dim.key];
        }
        document.querySelectorAll('#gs-presets .gs-btn').forEach(btn =>
            btn.setAttribute('aria-pressed', String(btn.dataset.preset === activePreset)));
    }

    /* ---------- Table + map ---------- */
    function visibleRows() {
        return rankedRows().filter(row => state.category === 'all' || row.category === state.category);
    }

    function renderTable() {
        const body = $('gs-table-body');
        const rows = visibleRows();
        body.replaceChildren(...rows.map(row => {
            const site = siteById(row.site_id);
            const button = el('button', { type: 'button', class: 'gs-row-btn', text: site.name, 'aria-label': `Show evidence for ${site.name}` });
            const tr = el('tr', {
                'data-site': row.site_id,
                class: `${row.category === 'control' ? 'is-control' : ''} ${state.selectedSite === row.site_id ? 'is-selected' : ''}`,
                onclick: () => selectSite(row.site_id),
            }, [
                el('td', { class: 'gs-num', text: String(row.liveRank) }),
                el('td', {}, [button, document.createTextNode(' '), categoryPill(row.category)]),
                el('td', {}, [el('div', { class: 'gs-bar', title: `${row.score.toFixed(1)}` }, [el('i', { style: `width:${Math.min(100, row.score)}%` })])]),
                el('td', { class: 'gs-num', text: row.score.toFixed(1) }),
                el('td', { class: 'gs-num', text: row.terrain.toFixed(0) }),
                el('td', { class: 'gs-num', text: row.environment.toFixed(0) }),
                el('td', { class: 'gs-num', text: row.geology.toFixed(0) }),
            ]);
            return tr;
        }));
    }

    function initMap() {
        if (state.map || typeof L === 'undefined') return;
        state.map = L.map('gs-map', { worldCopyJump: true, minZoom: 1, zoomSnap: 0.5 }).setView([20, 10], 2);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 10, attribution: '&copy; OpenStreetMap contributors',
        }).addTo(state.map);
        state.markerLayer = L.layerGroup().addTo(state.map);
        state.windowLayer = L.layerGroup().addTo(state.map);
    }

    function renderMap() {
        if (!state.map) return;
        state.markerLayer.clearLayers();
        for (const row of visibleRows()) {
            const site = siteById(row.site_id);
            const selected = state.selectedSite === row.site_id;
            const marker = L.circleMarker([site.lat, site.lon], {
                radius: selected ? 11 : 4 + Math.min(row.score, 70) / 10,
                color: selected ? '#ffffff' : '#0b1727', weight: selected ? 3 : 1.5,
                fillColor: colorFor(row.score, row.category), fillOpacity: 0.92,
            });
            marker.bindTooltip(`${site.name}: ${row.score.toFixed(1)} ACI (#${row.liveRank})`);
            marker.on('click', () => selectSite(row.site_id));
            marker.addTo(state.markerLayer);
        }
    }

    function drawBestWindow(row) {
        if (!state.map) return;
        state.windowLayer.clearLayers();
        const half = state.data.method.window_km / 2;
        const lat = row.best_window.lat;
        const lon = row.best_window.lon;
        const dLat = half / 111.32;
        const dLon = half / (111.32 * Math.max(Math.cos(lat * Math.PI / 180), 0.05));
        L.rectangle([[lat - dLat, lon - dLon], [lat + dLat, lon + dLon]], { color: '#ffd783', weight: 2, fillOpacity: 0.12 }).addTo(state.windowLayer);
    }

    /* ---------- Detail panel ---------- */
    function selectSite(siteId) {
        state.selectedSite = siteId;
        const row = rankedRows().find(r => r.site_id === siteId);
        renderTable();
        renderMap();
        renderDetail(row);
        drawBestWindow(row);
        if (state.map) state.map.flyTo([row.best_window.lat, row.best_window.lon], Math.max(state.map.getZoom(), 6), { duration: 0.6 });
    }

    function sharedTags(site, target) {
        return Object.entries(target.tags)
            .filter(([tag, weight]) => weight > 0 && (site.tags[tag] || 0) >= 0.5)
            .map(([tag]) => state.data.tag_vocabulary[tag] || tag);
    }

    function renderDetail(row) {
        const site = siteById(row.site_id);
        const target = currentTarget();
        const gapsBody = state.data.irreducible_gaps[target.body];
        const earth = state.data.irreducible_gaps.earth;
        $('gs-detail-title').textContent = site.name;
        $('gs-detail-sub').replaceChildren(categoryPill(site.category),
            document.createTextNode(` ${site.country}. Rank #${row.liveRank} of ${state.data.sites.length} for ${target.name}.`));

        const dims = $('gs-dims');
        dims.replaceChildren(...DIMENSIONS.map(d => el('div', { class: 'gs-dim', title: d.note }, [
            el('span', { text: d.label }),
            el('div', { class: 'gs-bar' }, [el('i', { style: `width:${row[d.key]}%` })]),
            el('span', { class: 'gs-num', text: `${row[d.key].toFixed(0)}%` }),
        ])));

        const robust = row.robust;
        $('gs-robust').textContent = `Under 1000 random weightings the default-weight rank ranges ${robust.rank_p10} to ${robust.rank_p90} (median ${robust.rank_median}); top-3 in ${(robust.prob_top3 * 100).toFixed(0)}% of draws.`;
        $('gs-window').replaceChildren(
            document.createTextNode(`Most Moon/Mars-like 40 km window: ${row.best_window.lat.toFixed(3)}, ${row.best_window.lon.toFixed(3)} `),
            el('a', { class: 'gs-link', target: '_blank', rel: 'noopener noreferrer', href: `https://www.openstreetmap.org/?mlat=${row.best_window.lat}&mlon=${row.best_window.lon}#map=9/${row.best_window.lat}/${row.best_window.lon}`, text: '(open map)' }),
            document.createTextNode(`. ${row.coverage.toFixed(0)}% of the region's ${row.n_windows} windows exceed 50% terrain similarity.`));

        const shared = sharedTags(site, target);
        $('gs-holds').replaceChildren(
            el('h3', { text: 'Where the analogy holds' }),
            el('p', { text: site.heritage }),
            el('div', { class: 'gs-tags' }, shared.length ? shared.map(tag => el('span', { class: 'gs-tag', text: tag })) : [el('span', { class: 'gs-note', text: 'No curated geology tags shared with this target.' })]),
        );
        const gaps = row.gaps.length ? row.gaps : ['No single measured gap exceeds the reporting threshold.'];
        $('gs-breaks').replaceChildren(
            el('h3', { text: 'Where it breaks down' }),
            el('ul', {}, [
                ...gaps.map(text => el('li', { text })),
                el('li', { text: site.limits }),
                el('li', { text: `Irreducible: gravity ${earth.gravity_ms2} vs ${gapsBody.gravity_ms2} m/s2, pressure ${earth.surface_pressure_kpa} vs ${gapsBody.surface_pressure_kpa} kPa, surface radiation ${earth.surface_radiation_msv_per_day} vs ${gapsBody.surface_radiation_msv_per_day} mSv/day.` }),
            ]));

        renderSlopeChart(row, target);
        const features = $('gs-features');
        features.replaceChildren(...Object.entries(row.env_features).map(([key, value]) =>
            el('div', { class: 'gs-dim' }, [
                el('span', { text: FEATURE_NAMES[key] || key }),
                el('div', { class: 'gs-bar' }, [el('i', { style: `width:${value}%` })]),
                el('span', { class: 'gs-num', text: `${value.toFixed(0)}%` }),
            ])));
        const c = site.climate;
        $('gs-climate').textContent = `NASA POWER: ${c.t_mean_c.toFixed(1)} C mean, ${c.t_daily_range_c.toFixed(1)} C daily range, ${c.precip_mm_yr.toFixed(0)} mm/yr, ${c.rel_humidity_pct.toFixed(0)}% humidity, ${c.surface_pressure_kpa.toFixed(0)} kPa.`;
        $('gs-detail').hidden = false;
    }

    function renderSlopeChart(row, target) {
        const canvas = $('gs-slope-chart');
        if (typeof Chart === 'undefined' || !canvas) return;
        if (state.chart) state.chart.destroy();
        const labels = row.slope_profile.baselines_m.map(b => `${b} m`);
        const validSet = new Set(target.valid_baselines_m);
        const targetValues = target.slope_profile.baselines_m.map((b, i) => validSet.has(b) ? target.slope_profile.median_deg[i] : null);
        const dataset = (label, data, color, dash) => ({ label, data, borderColor: color, backgroundColor: color, borderDash: dash || [], tension: 0.2, pointRadius: 3, spanGaps: false });
        state.chart = new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    dataset(`${target.name} (median)`, targetValues, '#ffd783'),
                    dataset('Earth site median', row.slope_profile.median_deg, '#68d7ee'),
                    dataset('Earth site p90', row.slope_profile.p90_deg, '#68d7ee', [5, 4]),
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#bcd3e4', boxWidth: 12, font: { size: 10 } } } },
                scales: {
                    x: { title: { display: true, text: 'Baseline length', color: '#8fb3c9' }, ticks: { color: '#8fb3c9' }, grid: { color: '#14293f' } },
                    y: { type: 'logarithmic', title: { display: true, text: 'Slope (deg)', color: '#8fb3c9' }, ticks: { color: '#8fb3c9' }, grid: { color: '#14293f' } },
                },
            },
        });
    }

    /* ---------- Static panels ---------- */
    function renderStaticPanels() {
        const { irreducible_gaps: gaps, validation, method, references } = state.data;
        const rowsData = [
            ['Gravity (m/s2)', gaps.earth.gravity_ms2, gaps.moon.gravity_ms2, gaps.mars.gravity_ms2],
            ['Surface pressure (kPa)', gaps.earth.surface_pressure_kpa, gaps.moon.surface_pressure_kpa, gaps.mars.surface_pressure_kpa],
            ['Surface radiation (mSv/day)', gaps.earth.surface_radiation_msv_per_day, gaps.moon.surface_radiation_msv_per_day, gaps.mars.surface_radiation_msv_per_day],
        ];
        $('gs-gap-body').replaceChildren(...rowsData.map(cells => el('tr', {}, cells.map(c => el('td', { text: String(c) })))));
        $('gs-gap-note').textContent = `${gaps.note} Moon: ${gaps.moon.other} Mars: ${gaps.mars.other}`;

        const moonAuc = mean(validation.per_target.filter(r => /shackleton|malapert/.test(r.target_id)).map(r => r.auc_aci));
        const marsAucAll = mean(validation.per_target.filter(r => !/shackleton|malapert/.test(r.target_id)).map(r => r.auc_aci));
        const weights = method.dimension_weights;
        const items = [
            `Default weights: terrain ${weights.terrain}, environment ${weights.environment}, geology ${weights.geology}; combined as a weighted geometric mean so a site must be adequate on every dimension. The additive mean is available from the controls.`,
            `Negative controls (${validation.control_sites.length} regions: plains, rainforest, glaciated and monsoon mountains) separate from analog candidates with AUC ${validation.mean_auc_aci.toFixed(2)} on average (additive mean: ${validation.mean_auc_aci_additive.toFixed(2)}; terrain alone ${validation.mean_auc_terrain.toFixed(2)}; environment alone ${validation.mean_auc_environment.toFixed(2)}; geology alone ${validation.mean_auc_geology.toFixed(2)}).`,
            `Lunar polar terrain is rugged, so steep mountain controls match its slope statistics. Terrain alone cannot reject them; environment and geology do, but Moon separation (AUC ${moonAuc.toFixed(2)}) is weaker than Mars (${marsAucAll.toFixed(2)}). Treat Moon rankings as hypotheses.`,
            `Environmental targets are clipped to the most extreme values reachable on Earth (${method.earth_floor.t_mean_c} C, ${method.earth_floor.surface_pressure_kpa} kPa, near-zero rain), so the dimension measures "as close as Earth gets", never equality. NASA POWER is a 0.5 degree reanalysis and is coarse for point sites.`,
            `Mars elevation comes from gridded MOLA (463 m); only baselines of ${method.mars_min_valid_baseline_m} m and longer are compared for Mars targets. Geology tags are curated expert priors, not measurements.`,
            'The ranking is a screening tool to decide where to look next. It does not replace field validation, and no site is claimed to be a confirmed analog.',
        ];
        $('gs-validation-list').replaceChildren(...items.map(text => el('li', { text })));
        $('gs-refs').replaceChildren(...references.map(text => el('li', { text })));
        $('gs-method-data').replaceChildren(...Object.values(method.data).map(text => el('li', { text })));
    }

    function refresh() {
        renderTable();
        renderMap();
        const rows = rankedRows();
        const selected = state.selectedSite && rows.find(r => r.site_id === state.selectedSite);
        if (selected) { renderDetail(selected); drawBestWindow(selected); }
        else if (!state.selectedSite) {
            const first = visibleRows()[0];
            if (first) { state.selectedSite = first.site_id; renderTable(); renderMap(); renderDetail(first); drawBestWindow(first); }
        }
    }

    async function init() {
        const root = $('global-tab');
        if (!root) return;
        try {
            const response = await fetch('global_results.json', { cache: 'no-store' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            state.data = await response.json();
        } catch (error) {
            const status = $('gs-status');
            if (status) { status.textContent = 'Global search results could not be loaded (global_results.json). Run python -m src.global_search.'; status.hidden = false; }
            return;
        }
        state.targetId = state.data.targets[0].id;
        window.__ptaeGlobal = state.data;
        renderSummary();
        renderHome();
        buildControls();
        renderStaticPanels();
        initMap();
        refresh();
        document.querySelectorAll('[data-gs-open]').forEach(node => node.addEventListener('click', () => {
            if (state.map) setTimeout(() => state.map.invalidateSize(), 150);
        }));
        $('tab-global')?.addEventListener('click', () => setTimeout(() => state.map?.invalidateSize(), 200));
        $('gs-reset-view')?.addEventListener('click', () => state.map?.setView([20, 10], 2));
    }

    window.addEventListener('load', init);
})();
