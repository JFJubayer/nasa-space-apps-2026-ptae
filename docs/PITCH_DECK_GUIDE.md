# NASA Space Apps 2026: Pitch Deck & Presentation Guide
## Project: PTAE (Planetary Terrestrial Analog Engine)

This guide provides a slide-by-slide structure, talking points, and a 30-second elevator pitch for presenting your project to the NASA Space Apps Challenge judges.

---

### ⏱️ The 30-Second Elevator Pitch
> *"Before astronauts travel to the lunar south pole region or touch down on Mars, every habitat, rover, and spacesuit must be rigorously stress-tested on Earth. But today, analog sites are chosen mostly by guesswork and qualitative impressions. We built **PTAE**, a demo that scores calibrated synthetic terrain matched to published morphometrics to discover and rank planetary analogs. The pipeline is designed to accept real LOLA, MOLA, and SRTM DEMs. Using our Analog Compatibility Index, we can identify promising locations on Earth—from Icelandic lava tubes to Antarctic dry valleys—that can help prepare crews for other worlds."*

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
- **Speaker Script:** "We developed PTAE. Our demo uses calibrated synthetic terrain matched to published morphometrics to calculate slope, roughness, and relief variance, then scores Earth candidates; the pipeline is designed to accept real LOLA, MOLA, and SRTM DEMs."

#### Slide 4: Scientific Methodology
- **Visual:** Side-by-side heatmaps of Elevation, Slope, and TRI; formula for ACI.
- **Key Points:**
  - **Slope ($^\circ$):** Critical for rover mobility, landing stability, and traverse routing.
  - **TRI (Terrain Ruggedness Index):** Quantifies micro-scale roughness and wheel-trap hazards.
  - **Environmental Modifiers:** Basaltic composition, hyper-aridity, and presence of lava tubes.
- **Speaker Script:** "Rather than just looking at pictures, we calculate the Riley Terrain Ruggedness Index and slope vectors across hundreds of square kilometers. We then score candidates against mission safety profiles."

#### Slide 5: The Top Discoveries
- **Visual:** Leaderboard ranking + radar chart screenshot from our dashboard.
- **Key Discoveries:**
  - **#1 Moon Demo Analog (calibrated synthetic terrain):** *McMurdo Dry Valleys, Antarctica (82.52% ACI)* — katabatic-carved slopes and fine-scale ruggedness matching lunar highland micro-roughness; Iceland's Askja Caldera is #2 (74.05%) for its lava-tube shielding.
  - **#1 Mars Demo Analog (calibrated synthetic terrain):** *Mauna Kea Cinder Cones, Hawaii (96.98% ACI; top-ranked analog)* — basaltic cinder-cone slopes mirroring Jezero Crater's rim and delta relief.
- **Speaker Script:** "Live, right now, our calibrated-synthetic-terrain demo ranks McMurdo Dry Valleys as an 82.52% topographic match for the lunar south pole region, with Askja at 74.05% — and Mauna Kea's cinder cones as the top Mars match at 96.98%, a top-ranked analog. Every number on this leaderboard is reproducible in under ten seconds by running `python main.py`. A real-data validation using a 20 m LRO LOLA Moon target and real Askja terrain showed scale sensitivity: the top candidate changes with window size, McMurdo ranks last in all windows, and Mauna Kea and Atacama stay in the top three."

#### Slide 6: Interactive Demo (Live Walkthrough)
- **Visual:** Screenshot of `dashboard/index.html` with active markers, Leaflet map, and radar charts.
- **Key Action:** Switch between Moon and Mars target in the live UI.
- **Speaker Script:** "We built an intuitive, responsive dashboard. In one click, mission teams can switch between Artemis Lunar South Pole and Mars Jezero Crater, viewing global candidates with instant quantitative breakdowns."

#### Slide 7: Vision & Future Impact
- **Visual:** Astronaut on lunar surface pointing to future roadmap.
- **Key Points:**
  - Google Earth Engine global continuous scanning.
  - Integration with mineralogical spectrometer data (CRISM / ASTER).
  - Open-source tool for NASA Artemis and international space agencies.
- **Speaker Script:** "By pairing calibrated terrain signatures with automated spatial analytics, PTAE helps identify the best ground on Earth for testing crews and rovers before they travel to other worlds. Thank you!"
