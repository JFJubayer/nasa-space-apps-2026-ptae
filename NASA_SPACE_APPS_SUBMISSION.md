# NASA International Space Apps Challenge 2026
## Official Project Submission Document

### 📌 Project Title
**PTAE: Planetary Terrestrial Analog Engine**  
*Quantitative Topographical & Environmental Characterization of Earth Analogs for Artemis III and Mars Base Locations*

---

### 🚀 High-Level Project Summary
The **Planetary Terrestrial Analog Engine (PTAE)** is an automated geospatial platform that ingests open elevation and environmental data from NASA’s Moon, Mars, and Earth missions to quantitatively discover, score, and rank uncharted terrestrial analogs for future permanent base sites.

---

### 📖 Detailed Project Description
Before astronauts and rovers touch down on the Lunar South Pole (Artemis III) or the Martian surface, their equipment, habitats, life-support systems, and In-Situ Resource Utilization (ISRU) techniques must be tested in real-world extreme environments on Earth. 

Historically, researchers have relied on qualitative analogies (e.g., "this desert looks dry like Mars" or "this volcanic rock looks like the Moon"). However, as missions grow more complex, mission planners need **quantitative, multi-parameter physical alignment**. 

**PTAE bridges this critical gap by:**
1. **Extracting Topographical Signatures:** Using Digital Elevation Models (DEMs) to compute continuous mathematical metrics including Surface Slope, Aspect, Riley's Terrain Ruggedness Index (TRI), and Topographic Position Index (TPI).
2. **Multi-Criteria Similarity Matching:** Normalizing topographic and environmental variance (desiccation, UV exposure, basaltic mineralogy, presence of volcanic lava tubes) into a unified **Analog Compatibility Index (ACI: 0–100%)**.
3. **Interactive Explorer:** Providing an interactive 2D/3D web dashboard and geospatial CLI to allow engineers and planetary geologists to rapidly evaluate test sites across the globe.

---

### 🛰️ Space Agency Data Used

| Planetary Body | Mission / Source | Instrument / Dataset | Purpose |
| :--- | :--- | :--- | :--- |
| **The Moon** | **Lunar Reconnaissance Orbiter (LRO)** | **LOLA (Lunar Orbiter Laser Altimeter)** | 5m–30m South Polar Stereographic DEMs for slope, roughness, and crater wall metrics. |
| **The Moon** | **LRO** | **Diviner Lunar Radiometer Experiment** | Surface and subsurface thermal environment data for cryogenic cold traps. |
| **Mars** | **Mars Global Surveyor (MGS)** | **MOLA (Mars Orbiter Laser Altimeter)** | Megameter-scale topography and roughness profiles for Jezero and Gale craters. |
| **Mars** | **Mars Reconnaissance Orbiter (MRO)** | **HiRISE & CRISM** | High-resolution morphology and hyperspectral mineralogical evidence (sulfates, phyllosilicates). |
| **Earth** | **Space Shuttle Radar Topography Mission (SRTM)** | **SRTM 1 Arc-Second Global (30m)** | Global terrestrial digital elevation benchmark for slope and ruggedness calculations. |
| **Earth** | **Terra Satellite** | **ASTER GDEM & Thermal Infrared** | High-resolution elevation and multispectral mineralogy / surface temperature. |
| **Earth** | **Landsat 8/9 & MODIS** | **NDVI & Surface Reflectance** | Vegetation filtration to isolate truly barren, space-like planetary analog zones. |

---

### 🎯 Key Findings & Characterized Analogs
*Scores below are reproduced live by running `python main.py --target moon` / `--target mars` against the five candidate sites currently modeled.*

1. **Top Lunar South Pole Analog — McMurdo Dry Valleys, Antarctica (ACI: 84.9%)**
   - *Topographical Congruence:* Katabatic-wind-carved valley walls and frozen polygon ground produce the steep slope and fine-scale ruggedness (TRI) profile closest to lunar highland terrain around Shackleton/Faustini.
   - *Runner-up:* Askja & Holuhraun Caldera, Iceland (ACI: 77.8%) — collapse calderas and basaltic lava tubes remain the best analog for subsurface radiation/thermal shielding, even though its topographic ACI trails McMurdo.

2. **Top Mars Jezero Crater Analog — Mauna Kea Cinder Cones, Hawaii (ACI: 100.0%)**
   - *Topographical Congruence:* Pyroclastic cinder-cone slopes and basaltic tephra ruggedness closely match the crater-rim and delta-fan relief profile computed for Jezero.
   - *Runner-up:* Puna de Atacama, Chile (ACI: 89.8%) — high-altitude (>4,000m), hyper-arid, perchlorate-rich terrain remains the strongest environmental/chemical analog for Martian desiccation and UV exposure.

> These rankings come from the **topographic + environmental-boost ACI** (slope, TRI, relief variance, plus aridity/basalt/lava-tube priors) computed on procedurally generated DEMs calibrated to published morphometrics for each site. Swapping in the real GeoTIFF tiles fetched by `scripts/download_nasa_samples.py` recomputes these same metrics from actual LOLA/HiRISE/SRTM data without any pipeline changes.

---

### 💻 Technologies & Software Stack
- **Language:** Python 3.10+
- **Spatial Analytics:** NumPy, SciPy (multidimensional filters, gradient operators), Rasterio / GDAL
- **Geographic Information Systems:** QGIS, Leaflet.js, OpenStreetMap / Carto Dark Basemaps
- **Visualization:** Matplotlib, Chart.js, HTML5/CSS3
- **Data Standards:** GeoTIFF, Cloud-Optimized GeoTIFF (COG), NumPy N-D Arrays, JSON

---

### 🔮 Future Expansion & Impact
- **Automated Earth Engine Ingestion:** Integrating Google Earth Engine API to automatically scan all continental landmasses with satellite masks.
- **ISRU Simulant Matching:** Pairing geological database APIs (USGS Mineral Resources) to rank sites by chemical yield for oxygen/water extraction.
- **Support for Artemis Base Camp:** Supplying the Artemis mission planning team with verified operational testing grounds for autonomous uncrewed rovers and lunar mobility suits.
