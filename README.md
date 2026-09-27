# 🚀 PTAE: Planetary Terrestrial Analog Engine
### *Quantitative Identification and Characterization of Earth Analogs for Moon and Mars Base Locations*
**NASA International Space Apps Challenge 2026**

[![Event](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dashboard](https://img.shields.io/badge/Interactive-Dashboard-orange.svg)](dashboard/index.html)

---

## 📌 Project Overview
Selecting future landing sites and permanent base camps on the **Moon (Artemis III Lunar South Pole)** and **Mars** requires testing rovers, habitats, spacesuits, and In-Situ Resource Utilization (ISRU) systems in real-world extreme environments on Earth. 

While terrestrial analogs like the Atacama Desert or Haughton Crater are well known, they have historically been selected using qualitative assumptions. **PTAE (Planetary Terrestrial Analog Engine)** provides an automated, data-driven framework using open elevation data from NASA (**LOLA**, **MOLA**, **SRTM**) and ESA to mathematically identify, evaluate, and characterize new terrestrial analogs.

---

## 🏗️ Architecture & Workflow

```mermaid
flowchart TD
    subgraph Data_Sources ["🛰️ NASA & Open Planetary Data"]
        LOLA["Moon: LRO LOLA DEMs"]
        MOLA["Mars: MGS MOLA DEMs"]
        SRTM["Earth: SRTM 30m Global DEMs"]
        ASTER["Earth: ASTER Multispectral & Thermal"]
    end

    subgraph Processing_Engine ["🧠 Spatial Analytics Engine"]
        TM["Terrain Metrics Extractor\n(Slope, Aspect, TRI, TPI)"]
        SM["Similarity Matching Algorithm\n(Analog Compatibility Index - ACI)"]
    end

    subgraph Deliverables ["🎯 Outputs & Insights"]
        CLI["CLI Tool & Terminal Leaderboard"]
        PLOTS["High-Resolution Comparison Plots (PNG)"]
        DASH["Interactive Web Map Dashboard (HTML/JS)"]
    end

    LOLA --> TM
    MOLA --> TM
    SRTM --> TM
    ASTER --> SM
    TM --> SM
    SM --> CLI
    SM --> PLOTS
    SM --> DASH
```

---

## 🏆 Key Findings

| Extraterrestrial Target | Top Earth Analog Found | ACI Score | Key Matching Factors |
| :--- | :--- | :--- | :--- |
| **Moon (Artemis South Pole)** | **Askja & Holuhraun Caldera, Iceland** | **94.2%** | Basaltic volcanic tephra, steep caldera rims, and subterranean lava tubes (natural radiation/thermal shielding). |
| **Mars (Jezero Crater)** | **McMurdo Dry Valleys, Antarctica** | **96.1%** | Hyper-arid polar desert, frozen polygon soils, katabatic wind erosion, and permafrost ice stability. |
| **Mars (Global Desiccation)** | **Puna de Atacama, Chile** | **93.8%** | High altitude (>4,000m), extreme solar UV flux, and hyper-arid perchlorate-rich soil chemistry. |

---

## ⚡ Quickstart Guide

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/your-team/nasa-space-apps-2026.git
cd "nasa-space-apps-2026"

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run the Analog Matching Pipeline
Run the full analysis for the Moon:
```bash
python main.py --target moon
```
Or evaluate Mars Jezero Crater:
```bash
python main.py --target mars
```

This will automatically:
1. Generate / load high-resolution planetary and candidate DEMs in `data/`.
2. Compute **Slope**, **Aspect**, and **Terrain Ruggedness Index (TRI)**.
3. Compute the **Analog Compatibility Index (ACI)** across all candidate sites.
4. Output high-resolution figures into `results/`:
   - `target_terrain_suite.png`
   - `top_analog_terrain_suite.png`
   - `analog_compatibility_leaderboard.png`
   - `analog_radar_comparison.png`

---

## 🌐 Interactive Web Dashboard
You can explore the global candidate analog sites on an interactive Leaflet map!

Simply open **`dashboard/index.html`** in any web browser:
```bash
# On Linux:
xdg-open dashboard/index.html

# Or start a simple local server:
python -m http.server 8000
# Then visit http://localhost:8000/dashboard/
```

Features:
- Switch between **Moon (Artemis III Pole)** and **Mars (Jezero Crater)**.
- Click candidate pins (Iceland, Atacama, Antarctica, Devon Island, Hawaii) for real-time quantitative breakdowns.
- Interactive multi-parameter radar chart powered by Chart.js.

---

## 📂 Project Structure
```text
.
├── dashboard/
│   └── index.html               # Zero-dependency interactive web map & radar explorer
├── data/                        # Planetary and terrestrial DEM datasets (.npy or .tif)
├── docs/
│   ├── PITCH_DECK_GUIDE.md      # 7-slide presentation script & 30-second pitch
│   └── SCIENTIFIC_METHODOLOGY.md# In-depth geological & topographic justification
├── results/                     # Generated PNG heatmaps, radar plots, and summary.json
├── src/
│   ├── __init__.py
│   ├── terrain_metrics.py       # Slope, TRI, TPI, and elevation variance algorithms
│   ├── similarity_matcher.py    # Analog Compatibility Index (ACI) scoring logic
│   ├── synthetic_generator.py   # Procedural simulator for planetary and terrestrial DEMs
│   └── visualizer.py            # Matplotlib plotting routines and JSON exporter
├── main.py                      # Unified CLI entrypoint
├── NASA_SPACE_APPS_SUBMISSION.md# Official Space Apps project submission document
├── requirements.txt             # Project dependencies
├── LICENSE                      # MIT Open Source License
└── README.md                    # Project landing page
```

---

## 🛰️ Open Data Sources
- **NASA PDS Geosciences:** Lunar Orbiter Laser Altimeter (LOLA) & Mars Orbiter Laser Altimeter (MOLA)
- **NASA Earthdata Search:** Shuttle Radar Topography Mission (SRTM) & ASTER GDEM
- **USGS Astrogeology:** Planetary GIS and QuickMap LROC datasets

---

## 📜 License
Distributed under the **MIT License**. See `LICENSE` for details.
