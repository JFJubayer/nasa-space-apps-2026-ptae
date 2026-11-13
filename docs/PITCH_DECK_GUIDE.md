# NASA Space Apps 2026: Pitch Deck & Presentation Guide
## Project: PTAE (Planetary Terrestrial Analog Engine), v2 on real data

> The recorded video in `docs/video/` and `docs/VIDEO_SCRIPT.md` still describe the v1 synthetic-terrain demo. Use this guide for live presentations.

### 30-second pitch
> "Before astronauts reach the lunar south pole or Mars, hardware and procedures are tested on Earth, but analog sites are mostly chosen by tradition. PTAE scans 33 Earth regions, including 14 little-studied ones, against 8 Moon and Mars targets using real LOLA, MOLA and SRTM elevation plus NASA climate data. For every match it shows where the analogy holds and where it breaks down. For Mars, four of our top five regions are deserts that rarely appear on analog lists, and the classic Atacama still shows up, which tells us the method works."

### Slide structure

**1. Title and hook.** *Finding, ranking and critiquing Earth analogs for the Moon and Mars.* Question to open: "Where on Earth is a good stand-in, and for what?"

**2. The challenge.** Quote the brief: do not just rediscover famous sites; explain what is similar and what is not. Analog sites are poorly characterized and picked qualitatively.

**3. Our approach (one diagram).** Real data (LOLA, MOLA, SRTM-based tiles, NASA POWER) -> multi-baseline terrain signature -> three dimensions (terrain, climate, geology) -> ranking with uncertainty and "where it breaks down".

**4. Why the method is sound.**
- Slope is measured over identical ground baselines (240 m to 3.84 km), so a 20 m lunar DEM and a 463 m Mars DEM are comparable.
- Sliding 40 km windows find the best sub-region inside a large area and show it on the map.
- Environment targets are clipped to what Earth can actually reach, so "similar" never means "equal".
- Scores are combined multiplicatively: a site must pass every dimension.

**5. Findings (reproducible with `python -m src.global_search`).**
- Mars: Gilf Kebir (Egypt), Dasht-e Lut (Iran), Qaidam Basin (China), Pinacate (Mexico), then Atacama Yungay.
- Moon: Death Valley, McMurdo Dry Valleys, Tibesti (Chad).
- Negative controls (rainforest, plains, glaciated and monsoon mountains) are separated from candidates with AUC 0.84 for Mars and 0.66 for the Moon.

**6. Honesty slide.** The Moon result is weaker because steep mountains match lunar polar slopes; MOLA limits Mars to kilometre-scale terrain; NASA POWER is coarse; geology tags are curated. Earth cannot reproduce gravity, vacuum or radiation (show the dashboard table).

**7. Live demo (60 seconds).** Open the Global Search tab. Pick Jezero Crater, click Qaidam Basin, show the yellow best-window box, the slope chart and the "where it breaks down" panel. Switch to the Rover preset and watch the ranking change. Switch to Shackleton and point out the weaker Moon separation.

**8. Vision.** HiRISE/CTX DEMs for rover-scale roughness, Diviner temperatures and illumination for lunar targets, mineral maps for geology, and a true global grid scan.

### Likely judge questions
- *Is this validated?* Negative-control AUC and rank-stability under random weights; no ground-truth analog database exists, so we say so.
- *Why trust geology tags?* They are labelled as curated priors and carry 25% default weight, adjustable by the user.
- *Why not machine learning?* There are too few labelled analog sites; the scoring is transparent and its inputs can be inspected per region.
- *Was AI used?* Yes; see the SI disclosure in the README and the submission.
