# PTAE: Planetary Terrestrial Analog Engine
### Finding, ranking and critiquing Earth analogs for Moon and Mars exploration sites
**NASA International Space Apps Challenge 2026** - *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*

[![Event](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

PTAE scans 33 Earth regions, including 14 less-studied ones and 5 deliberate negative controls, against 8 Moon and Mars targets using **real NASA data**. For every pairing it shows *where the analogy holds and where it breaks down*. It runs on open data from one command.

## What is new in v2

| Weakness of v1 | Fix in v2 |
| :--- | :--- |
| Procedural (synthetic) terrain | Real elevation: LRO LOLA (Moon), MGS MOLA (Mars), SRTM/NASADEM-based AWS Terrain Tiles (Earth) |
| Five famous sites only | 33 regions: 14 benchmarks, 14 less-studied candidates, 5 negative controls |
| Terrain only, plus a boolean bonus | Three dimensions: terrain, NASA POWER climate, curated geology |
| Pixel-scale slope compared across 20 m, 30 m and 463 m DEMs | Slope over identical ground baselines (240 m to 3.84 km), so resolution cancels |
| One window per site | Sliding 40 km windows find the best sub-region; the map shows exactly where |
| Gaussian on means, single score | Rank uncertainty from 1000 random weightings, plus negative-control AUC |
| Earth treated as a perfect analog | Explicit "where it breaks down" panel and the conditions no Earth site can reproduce |

## Results

Mean ACI across targets (0 to 100, a relative index; Earth never reaches 100):

| Body | Top 5 |
| :--- | :--- |
| **Mars** (Jezero, Gale, Gusev, Meridiani, Oxia, Hellas) | Gilf Kebir, Egypt (51); Dasht-e Lut, Iran (50); Qaidam Basin, China (48); Pinacate, Mexico (45); Atacama Yungay, Chile (38) |
| **Moon** (Shackleton, Malapert) | Death Valley, USA (44); McMurdo Dry Valleys, Antarctica (42); Tibesti, Chad (37); Bernese Alps (control, 35); Dasht-e Lut, Iran (33) |

Takeaways:
- For Mars, four of the five best regions are **less-studied deserts**, and the benchmark Atacama still ranks in the top five, which is the expected sanity check.
- Negative controls (rainforest, plains, glaciated and monsoon mountains) are separated from candidates with AUC 0.84 on Mars targets.
- **The Moon result is weaker (AUC 0.66).** Lunar polar terrain is rugged, so steep mountain controls match its slope statistics; only climate and geology reject them. Treat Moon rankings as hypotheses.
- Terrain alone separates controls from candidates with AUC 0.64, climate 0.86 and geology 0.95. The dimensions are complementary, so scores are combined multiplicatively (a site must be adequate on every dimension).

Full per-target tables: [results/global_ranking.csv](results/global_ranking.csv) and the dashboard.

## Method in brief
1. **Data.** Earth: AWS Terrain Tiles (zoom 11). Moon: LOLA 20 m south-polar DEM. Mars: MOLA 463 m. All resampled to a common 120 m grid and 40 km windows.
2. **Terrain signature.** Median and 90th-percentile slope over baselines of 240, 480, 960, 1920 and 3840 m, plus Hurst exponent and relief (differential-slope method; Kreslavsky and Head 2000; Rosenburg et al. 2011). Mars uses only baselines of 960 m and longer because gridded MOLA does not resolve finer terrain.
3. **Environment.** NASA POWER climatology (mean temperature, daily range, rain, humidity, pressure) compared with a target clipped to the most extreme values reachable on Earth.
4. **Geology.** Curated tags (impact, basaltic, lava tubes, ground ice, evaporites, and so on) in [catalog/](catalog/). These are expert priors, not measurements, and are labelled as such.
5. **Score.** Weighted geometric mean of the three similarities (default 0.5 / 0.25 / 0.25). The additive mean is available in the dashboard.
6. **Uncertainty and validation.** 1000 random weightings per target; negative-control AUC; best-window coverage.

### Limitations
- The aggregation was changed from additive to geometric after we saw that the additive form let a wet alpine valley rank first for the Moon. Both are reported; the geometric form does not remove the Moon weakness.
- NASA POWER is a 0.5 degree reanalysis and is coarse for single sites (it over-estimates rain in Iceland, for example).
- Gridded MOLA limits Mars comparisons to kilometre-scale terrain; rover-scale roughness needs HiRISE or CTX DEMs.
- Geology tags and the "emerging" label are judgement, not data. Rankings guide where to look next; they do not confirm analogs.
- Earth cannot reproduce gravity, vacuum or Mars pressure, or the radiation environment (see the dashboard table).

## Quickstart
```bash
git clone https://github.com/JFJubayer/nasa-space-apps-2026-ptae.git
cd nasa-space-apps-2026-ptae
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.global_search                         # downloads real data (cached in cache/), writes dashboard/global_results.json
python -m http.server --directory dashboard 8000    # open http://localhost:8000/
```
Open the **Global Search** tab, choose a Moon or Mars target, change the mission-priority sliders, and click any region.

Tests (offline): `python -m unittest discover -s tests -v`. Browser tests also need `pip install -r requirements-dev.txt && python -m playwright install chromium`.

## Repository layout
```text
catalog/                 Earth sites and Moon/Mars targets (curated tags, heritage, limits)
src/geodata.py           Fetch LOLA, MOLA, terrain tiles, NASA POWER
src/multiscale.py        Baseline slope signatures, sliding windows, water masking
src/analog_score.py      Terrain/environment/geology similarity, aggregation, robustness, AUC
src/global_search.py     End-to-end pipeline and CLI
dashboard/               Static web app (Global Search tab plus the original v1 demo tabs)
tests/                   Unit tests for v2 and for the v1 pipeline
main.py, src/terrain_metrics.py, similarity_matcher.py, synthetic_generator.py
                         v1 synthetic-terrain demo, kept for the original tabs and tests
```

## v1 synthetic demo (legacy)
`python main.py --target moon --json-out` and `--target mars` still regenerate the calibrated synthetic-terrain demo used by the dashboard's "Explore Sites" and "Compare" tabs. Those scores are **not** measurements; use Global Search for real-data results.

## Open data and references
LRO LOLA (NASA PGDA), MGS MOLA (USGS Astrogeology), AWS Terrain Tiles (SRTM, NASADEM, ArcticDEM and others), NASA POWER. References are listed in the dashboard and in [docs/SCIENTIFIC_METHODOLOGY.md](docs/SCIENTIFIC_METHODOLOGY.md).

## Use of Super Intelligence (SI) tools
Per the Space Apps rules: the v1 prototype was drafted with an AI assistant, and the v2 redesign (data pipeline, scoring, dashboard tab, tests, documentation) was developed with GitHub Copilot. Design decisions, data choices and validity checks remain the team's responsibility.

## License
MIT. See [LICENSE](LICENSE).
