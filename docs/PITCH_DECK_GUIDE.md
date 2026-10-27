# NASA Space Apps 2026: Pitch Deck & Presentation Guide
## Project: PTAE (Planetary Terrestrial Analog Engine)

This guide provides a slide-by-slide structure, talking points, and a 30-second elevator pitch for presenting your project to the NASA Space Apps Challenge judges.

---

### ⏱️ The 30-Second Elevator Pitch
> *"Before astronauts travel to the lunar south pole region or Mars, their equipment is tested on Earth. We built **PTAE** to compare terrain statistics from 20 Earth field sites against lunar and Martian target DEMs. The current real-data results rank Teide at 87.22% for the Moon target and Kilauea at 55.84% for Jezero. These ACI values measure terrain-statistics similarity, not mission suitability; Mars and Earth DEM resolutions differ."*

The new sensitivity analysis covers only center crops of the existing window (no larger windows); mappings for added sites are provisional; the default synthetic demo and legacy `results.json` cover only the original five sites.

---

### 📊 7-Slide Pitch Deck Structure

#### Slide 1: Title & Hook
- **Visual:** High-contrast split image showing the Lunar South Pole (Shackleton crater) next to an Icelandic volcanic caldera.
- **Header:** PTAE: Planetary Terrestrial Analog Engine
- **Subtitle:** *Finding Humanity's Training Grounds for the Moon and Mars*
- **Speaker Script:** "Good day judges. When NASA prepares to establish a permanent base camp on the Moon, where do we test our tech first? Earth. But where on Earth actually matches the Moon?"

#### Slide 2: The Challenge
- **Visual:** Map showing traditional analog sites (Atacama, Death Valley) with a question mark over their true suitability.
- **Key Points:**
  - Terrestrial analogs are poorly characterized.
  - Qualitative selection leads to unexpected equipment failures in space.
  - We need quantitative, multi-parameter physical alignment.
- **Speaker Script:** "Until now, picking analog sites has been largely qualitative—'it's a desert, so it's like Mars.' But the Moon's South Pole has steep 20° crater rims, sharp basaltic glass, and extreme thermal gradients. Testing in the wrong terrain puts multi-billion dollar missions at risk."

#### Slide 3: Our Solution
- **Visual:** Diagram of the PTAE pipeline (NASA Open Data $\rightarrow$ Topographical Engine $\rightarrow$ Similarity Matcher $\rightarrow$ Interactive Dashboard).
- **Key Points:**
  - Automated quantitative matching engine.
  - Combines Surface Slope, Riley's Terrain Ruggedness (TRI), and Relief Variance.
  - Introduces the **Analog Compatibility Index (ACI)**.
- **Speaker Script:** "We developed PTAE. Its current ranking uses a south-polar LRO LOLA target, a Jezero MOLA target, and AWS Terrain Tiles DEM windows for 20 Earth candidates. Prepared 300-by-300 grids feed slope, roughness, and elevation-variation metrics into the ACI."

#### Slide 4: Scientific Methodology
- **Visual:** Side-by-side heatmaps of Elevation, Slope, and TRI; formula for ACI.
- **Key Points:**
  - **Slope ($^\circ$):** Critical for rover mobility, landing stability, and traverse routing.
  - **TRI (Terrain Ruggedness Index):** Quantifies micro-scale roughness and wheel-trap hazards.
  - **Environmental Modifiers:** Additive catalog-flag bonus for basaltic terrain, hyper-aridity, and lava tubes.
- **Speaker Script:** "Rather than just looking at pictures, we compare slope and Riley's Terrain Ruggedness Index as terrain statistics; the DEM windows differ in resolution and physical footprint. A fixed weighted similarity model ranks those statistics; it is not a validated mission-safety profile."

#### Slide 5: The Top Discoveries
- **Visual:** Leaderboard ranking + radar chart screenshot from our dashboard.
- **Key Discoveries:**
  - **#1 Moon terrain-statistics match:** *Teide / Tenerife Volcanic Field (87.22% ACI)*; runner-up *Mount Etna (86.79%)*.
  - **#1 Mars terrain-statistics match:** *Kilauea Volcanic Field (55.84% ACI)*; runner-up *Craters of the Moon, Idaho (54.99%)*.
- **Speaker Script:** "Our current sidecar-backed results rank Teide first for the lunar target at 87.22%, with Etna second at 86.79%. For Jezero, Kilauea ranks first at 55.84%, followed by Craters of the Moon at 54.99%. These are terrain-statistics similarities, not evidence of mission suitability. The Mars target is about 334 meters per pixel while the Earth windows are about 33 meters per pixel, so Mars scores are indicative and not directly comparable."
- **Reproduce the current rankings:** Run `python scripts/fetch_site_dems.py`, then run `python main.py --target moon --use-existing-data --data-dir data_real --no-vis --json-out dashboard/results_moon.json` and the corresponding `--target mars` command for `dashboard/results_mars.json`.

#### Slide 6: Interactive Demo (Live Walkthrough)
- **Visual:** Screenshot of `dashboard/index.html` with the CesiumJS globe, 20 Earth candidate markers, and radar chart; Leaflet is the Earth fallback.
- **Key Action:** Switch between Moon and Mars target in the live UI.
- **Speaker Script:** "We built a responsive dashboard that loads all 20 catalog-listed Earth sites, their JSON rankings, and per-site DEM provenance. Teams can switch between Earth, the lunar south-pole target, and Jezero, then inspect site details and the current target's ACI breakdown."

#### Slide 7: Vision & Future Impact
- **Visual:** Astronaut on lunar surface pointing to future roadmap.
- **Key Points:**
  - Google Earth Engine global continuous scanning.
  - Integration with mineralogical spectrometer data (CRISM / ASTER).
  - Open-source tool for NASA Artemis and international space agencies.
- **Speaker Script:** "By pairing DEM-derived terrain statistics with a reproducible ranking workflow, PTAE helps researchers compare candidate field sites. The scores are exploratory terrain similarities, not proof that a site is the best or operationally suitable test ground. Thank you!"
