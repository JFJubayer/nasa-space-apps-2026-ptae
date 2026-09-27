# NASA Space Apps 2026: Pitch Deck & Presentation Guide
## Project: PTAE (Planetary Terrestrial Analog Engine)

This guide provides a slide-by-slide structure, talking points, and a 30-second elevator pitch for presenting your project to the NASA Space Apps Challenge judges.

---

### ⏱️ The 30-Second Elevator Pitch
> *"Before astronauts set foot on the Lunar South Pole with Artemis III or touch down on Mars, every habitat, rover, and spacesuit must be rigorously stress-tested on Earth. But today, analog sites are chosen mostly by guesswork and qualitative impressions. We built **PTAE**, an automated platform that processes open NASA elevation and environmental data to quantitatively discover and rank true planetary analogs. Using our Analog Compatibility Index, we can pinpoint the exact locations on Earth—from Icelandic lava tubes to Antarctic dry valleys—that will ensure humanity's permanent survival on other worlds."*

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
- **Speaker Script:** "We developed PTAE. Our tool extracts digital elevation models from NASA's LOLA and MOLA planetary instruments, calculates slope, roughness, and relief variance, and matches them mathematically with Earth's global SRTM elevation data."

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
  - **#1 Moon Analog:** *Askja Caldera, Iceland (94.2% ACI)* — Basaltic tephra + subterranean lava tubes for radiation shelter.
  - **#1 Mars Analog:** *McMurdo Dry Valleys, Antarctica (96.1% ACI)* — Frozen polygon permafrost + cold desiccation.
- **Speaker Script:** "Our engine revealed that the Askja and Holuhraun caldera in Iceland is a 94.2% match for the Artemis III landing zone, not only for steep slopes, but because its lava tubes directly analog lunar underground shelters."

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
- **Speaker Script:** "By pairing open NASA data with automated spatial analytics, PTAE ensures that every crew and rover deployed to the stars is tested on the best ground Earth has to offer. Thank you!"
