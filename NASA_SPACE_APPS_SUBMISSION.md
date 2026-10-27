# NASA International Space Apps Challenge 2026
## Official Project Submission Document

### 📌 Project Title
**PTAE: Planetary Terrestrial Analog Engine**  
*Quantitative Topographical & Environmental Characterization of Earth Analogs for Artemis III and Mars Base Locations*

---

### 🚀 High-Level Project Summary
The **Planetary Terrestrial Analog Engine (PTAE)** is an automated geospatial prototype that ranks 20 catalog-listed Earth sites against lunar and Martian terrain statistics. The checked-in current rankings use real LRO LOLA and MOLA target DEMs plus real AWS Terrain Tiles DEMs for all 20 Earth candidates. The default CLI mode remains a separate procedural synthetic demo.

---

### 📖 Detailed Project Description
Before astronauts and rovers operate in the lunar south pole region or on the Martian surface, their equipment, habitats, life-support systems, and In-Situ Resource Utilization (ISRU) techniques must be tested in real-world extreme environments on Earth.

Historically, researchers have relied on qualitative analogies (e.g., "this desert looks dry like Mars" or "this volcanic rock looks like the Moon"). However, as missions grow more complex, mission planners need **quantitative, multi-parameter physical alignment**. 

**PTAE bridges this critical gap by:**
1. **Extracting Topographical Signatures:** Using Digital Elevation Models (DEMs) to extract slope, Riley's Terrain Ruggedness Index (TRI), TPI, and elevation statistics. TPI is extracted but not scored; Aspect is not computed by signature extraction.
2. **Multi-Criteria Similarity Matching:** Computing the **Analog Compatibility Index (ACI: 0–100%)** from five terrain metrics (slope mean/std, TRI mean/std, and elevation std) plus an additive candidate-only flag bonus for hyper-aridity, basaltic terrain, and lava tubes.
3. **Interactive Explorer:** Providing an interactive 2D/3D web dashboard and geospatial CLI to allow engineers and planetary geologists to rapidly evaluate test sites across the globe.

---

### 🛰️ Space Agency Data Sources

| Planetary Body | Mission / Source | Instrument / Dataset | Purpose |
| :--- | :--- | :--- | :--- |
| **The Moon** | **Lunar Reconnaissance Orbiter (LRO)** | **LOLA (Lunar Orbiter Laser Altimeter)** | South-polar target DEM; 20 m source resampled to 300×300 at 33.40 m/pixel for the current run. |
| **The Moon** | **LRO** | **Diviner Lunar Radiometer Experiment** | Surface and subsurface thermal environment data for cryogenic cold traps. |
| **Mars** | **Mars Global Surveyor (MGS)** | **MOLA (Mars Orbiter Laser Altimeter)** | Jezero target DEM; the prepared 300×300 grid is 333.69 m/pixel. |
| **Mars** | **Mars Reconnaissance Orbiter (MRO)** | **HiRISE & CRISM** | High-resolution morphology and hyperspectral mineralogical evidence (sulfates, phyllosilicates). |
| **Earth** | **AWS Terrain Tiles** | **Zoom 10 GeoTIFF terrain tiles** | Current source for all 20 catalog candidates; each 10 km window is resampled to 300×300 at approximately 33.3–33.5 m/pixel. |
| **Earth** | **Space Shuttle Radar Topography Mission (SRTM)** | **SRTM 1 Arc-Second Global (30m)** | Reference/future source; not used in the current AWS candidate run. |
| **Earth** | **Terra Satellite** | **ASTER GDEM & Thermal Infrared** | High-resolution elevation and multispectral mineralogy / surface temperature. |
| **Earth** | **Landsat 8/9 & MODIS** | **NDVI & Surface Reflectance** | Vegetation filtration to isolate truly barren, space-like planetary analog zones. |

Diviner, HiRISE/CRISM, ASTER, and Landsat/MODIS are reference or future data sources, not inputs to the current ACI runs. Prepared target and Earth DEM provenance and resolutions are recorded in `data_real/*.json`.

---

### 🎯 Key Findings & Characterized Analogs
The current result files rank all 20 Earth candidates using the prepared real DEMs. The default commands without `--use-existing-data` still produce a separate synthetic demo.

1. **Moon south-polar terrain-statistics leader — Teide / Tenerife Volcanic Field (ACI: 87.22%)**
   - *Second-ranked:* Mount Etna (ACI: 86.79%).

2. **Mars Jezero terrain-statistics leader — Kilauea Volcanic Field (ACI: 55.84%)**
   - *Second-ranked:* Craters of the Moon, Idaho (ACI: 54.99%).

> These are weighted terrain-statistics similarities over slope, TRI, elevation variation, and catalog flags. They are not proof of mission suitability or operational readiness. Mars and Earth input resolutions differ substantially, so Mars scores are indicative only.

**Weight robustness:** Moon Teide stays #1 in 92.83% of 1,018 scenarios (top-3: 100%); Mars Kilauea stays #1 in 22.30% (top-3: 42.34%). Four deterministic Mars scenarios change the leader (Craters of the Moon x3, Svalbard x1). Percentages describe the chosen scenario mix, not scientific probabilities; this tests weight robustness, not correctness of weights or flags.

The separate `window_sensitivity.json` preserves a historical Moon-window experiment using real LOLA and Askja plus four synthetic Earth candidates, so its five-site leaders are not the current 20-site results. It also contains a new Moon/Mars sensitivity run across all 20 real Earth DEMs using centered 300×300, 225×225, and 150×150 crops at each input's unchanged pixel resolution; physical window size therefore shrinks with crop size. The `target_sites.json` qualitative mappings for added candidates are provisional and separate from the ACI ranking.

For 14 of the 15 added Earth sites, AWS DEMs were upsampled from ~55.5-76.2 m/pixel to ~33 m/pixel; Svalbard was downsampled from 15.65 to 33.34 m/pixel. Upsampling does not add terrain detail. The Mars grid was resampled from ~451 to ~334 m/pixel and spans ~100 km per side, versus ~10 km for Earth windows. Flags on added sites are unverified. DEM metrics check terrain morphology only, not geology.

The new sensitivity analysis covers only center crops of the existing window (no larger windows); mappings for added sites are provisional; the default synthetic demo and legacy `results.json` cover only the original five sites.

---

### 💻 Technologies & Software Stack
- **Language:** Python 3.10+
- **Spatial Analytics:** NumPy, SciPy (multidimensional filters, gradient operators), Rasterio / GDAL
- **Geographic Visualization:** CesiumJS globe, Leaflet fallback for Earth, OpenStreetMap tiles
- **Visualization:** Matplotlib, Chart.js, Three.js, HTML5/CSS3
- **Data Standards:** GeoTIFF, Cloud-Optimized GeoTIFF (COG), NumPy N-D Arrays, JSON

---

### 🔮 Future Expansion & Impact
- **Automated Earth Engine Ingestion:** Integrating Google Earth Engine API to automatically scan all continental landmasses with satellite masks.
- **ISRU Simulant Matching:** Pairing geological database APIs (USGS Mineral Resources) to rank sites by chemical yield for oxygen/water extraction.
- **Potential future use:** Explore whether better-characterized field sites can support autonomous rover and lunar mobility testing. Current rankings do not verify operational suitability.
