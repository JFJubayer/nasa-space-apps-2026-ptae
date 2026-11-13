# NASA International Space Apps Challenge 2026
## Project Submission Document

### Project title
**PTAE: Planetary Terrestrial Analog Engine**
*A global, multi-dimensional search for Earth analogs of Moon and Mars exploration sites, with explicit limits of each analogy*

### Challenge
Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.

### High-level summary
PTAE compares 33 Earth regions with 8 Moon and Mars targets using real LOLA, MOLA and SRTM-based elevation data and NASA POWER climate. Terrain is compared with slope statistics over identical ground baselines, so 20 m, 30 m and 463 m data are comparable. Each pairing is scored on terrain, climate and geology, combined so that a site must be adequate on every dimension. The dashboard shows, per region, where the analogy holds, where it breaks down, the best 40 km window, and how stable the ranking is.

### Why this answers the brief
| The brief asks | PTAE |
| :--- | :--- |
| Use open Earth, Moon and Mars data from NASA and others | LRO LOLA 20 m, MGS MOLA 463 m, AWS Terrain Tiles (SRTM/NASADEM/ArcticDEM), NASA POWER |
| Do not only rediscover famous analogs | 14 less-studied regions (e.g. Gilf Kebir, Dasht-e Lut, Qaidam Basin, Harrat Khaybar, Tibesti) are scored beside 14 benchmarks |
| Think beyond visual similarity; several dimensions | Terrain (measured), climate (measured), geology and subsurface tags (curated) |
| Explain what is similar, how similar, and what is different | Per-region "holds / breaks down" panel with measured gaps and site-specific limits |
| Consider scale; a small area may beat a whole region | Sliding 40 km windows; the best window is mapped and coverage is reported |
| Remember Earth's limits | Table of gravity, pressure and radiation that no Earth site can reproduce; environmental targets are clipped to Earth-achievable values |
| Show it as a map, visualization or tool | Interactive map, ranking, slope charts, mission-priority sliders |

### Key findings (default weights; reproduce with `python -m src.global_search`)
- **Mars (mean over Jezero, Gale, Gusev, Meridiani, Oxia, Hellas):** Gilf Kebir, Egypt (51); Dasht-e Lut, Iran (50); Qaidam Basin, China (48); Pinacate, Mexico (45); Atacama Yungay, Chile (38). Four of the top five are less-studied deserts; a well-known benchmark still appears, as expected.
- **Moon (mean over Shackleton and Malapert):** Death Valley (44); McMurdo Dry Valleys (42); Tibesti, Chad (37); Bernese Alps (35, a negative control); Dasht-e Lut (33).
- **Validation:** negative controls (rainforest, plains, glaciated and monsoon mountains) are separated from candidates with AUC 0.84 for Mars targets and 0.66 for Moon targets. The Moon result is weaker because lunar polar terrain is rugged and steep mountains match its slope statistics. We report this rather than hide it, and treat Moon rankings as hypotheses.
- **Dimensions are complementary:** AUC against controls is 0.64 for terrain alone, 0.86 for climate alone and 0.95 for geology alone.

### Limitations
Gridded MOLA limits Mars to kilometre-scale terrain; NASA POWER is a 0.5 degree reanalysis; geology tags and the "emerging" label are expert judgement; the aggregation was changed from additive to geometric after observing that the additive form favoured a wet alpine control (both are reported). Rankings guide where to look next and do not confirm analogs.

### Data sources
| Body | Source | Use |
| :--- | :--- | :--- |
| Moon | LRO LOLA 20 m south-polar DEM (NASA PGDA) | Terrain of Shackleton and Malapert regions |
| Mars | MGS MOLA 463 m global DEM (USGS Astrogeology) | Terrain of six landing and exploration regions |
| Earth | AWS Terrain Tiles (SRTM, NASADEM, ArcticDEM and others) | Terrain of 33 regions, 80 km areas scanned with 40 km windows |
| Earth | NASA POWER climatology (2001-2025) | Temperature, daily range, precipitation, humidity, pressure |
| Moon, Mars | Published values (Chang'E-4 LND, MSL RAD, LRO Diviner) | Gravity, pressure and radiation gap table |

### Technology
Python (NumPy, SciPy, rasterio, pyproj, Pillow), static web dashboard (Leaflet, Chart.js, vanilla JavaScript), unit tests. Everything is reproducible from open data with one command.

### Use of Super Intelligence (SI) tools
The challenge rules require a description of SI use. The v1 prototype (synthetic terrain, five-site demo, video and presentation assets) was drafted with an AI assistant. The v2 redesign (real-data pipeline, multi-baseline terrain method, three-dimension scoring, robustness and negative-control validation, the Global Search dashboard tab, tests and documentation) was developed with GitHub Copilot under the team's direction. The team chose the data sources and the validity checks and is responsible for the content.

### Future work
- Replace gridded MOLA with HiRISE/CTX DEMs and LOLA-derived rock-abundance products for rover-scale comparison.
- Add Diviner temperature statistics and illumination (Sun and Earth visibility) for lunar targets, and thermal inertia or NDVI masks for Earth.
- Move from a curated long-list to a true global grid scan, with machine-learned similarity once more labelled analog sites exist.
- Replace curated geology tags with mineral maps (e.g. ASTER, CRISM-matched indices).
