# Scientific Methodology & Geological Grounding
## Quantitative Planetary Analog Characterization

### 1. Introduction & Physical Motivation
Planetary analog studies are foundational to mission risk reduction. Uncrewed rovers (e.g., Curiosity, Perseverance, VIPER) and crewed exploration architectures (Artemis III/IV, Mars Base Camp) are constrained by severe physical limitations in locomotion, communication geometry, solar illumination, and thermal control. 

This document defines the mathematical formulation and physical justification of the metrics implemented in the **Planetary Terrestrial Analog Engine (PTAE)**.

---

### 2. Topographical Metric Formulations

#### 2.1 Surface Slope ($\theta$)
Slope represents the maximum rate of change in elevation from a cell to its immediate neighbors. 

Given a continuous elevation surface $z = f(x, y)$, the gradient vector is:
$$\nabla z = \left( \frac{\partial z}{\partial x}, \frac{\partial z}{\partial y} \right)$$

The slope angle in degrees is calculated as:
$$\theta = \arctan \left( \sqrt{ \left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2 } \right) \times \frac{180}{\pi}$$

**Mission Relevance:**
- Rover wheels and tracks typically slip or incur high torque stall risks at slopes exceeding $15^\circ - 20^\circ$.
- Lunar landers require landing ellipse slopes $< 10^\circ - 12^\circ$ to prevent tip-over upon touchdown.

---

#### 2.2 Riley's Terrain Ruggedness Index (TRI)
The Terrain Ruggedness Index (Riley et al., 1999) quantifies the total elevation change between a central grid cell and its surrounding eight orthogonal and diagonal neighbors:

$$\text{TRI} = \sqrt{ \sum_{i=-1}^{1} \sum_{j=-1}^{1} (z_{0,0} - z_{i,j})^2 }$$

Where $z_{0,0}$ is the elevation of the central pixel and $z_{i,j}$ are the elevations of the 8 neighbors.

**Mission Relevance:**
- Unlike slope, which indicates average inclination, TRI captures high-frequency topographic roughness (micro-craters, boulder fields, fault scarps, and ejecta blocks).
- High TRI indicates mobility hazards and wheel-trap regions.

---

#### 2.3 Topographic Position Index (TPI)
TPI measures the relative topographic position of a point compared to the surrounding regional neighborhood within radius $R$:

$$\text{TPI} = z_{0,0} - \bar{z}_{R}$$

Where $\bar{z}_{R}$ is the average elevation of the surrounding cells.
- $\text{TPI} > 0$: Rims, ridges, elevated peaks (good for solar line-of-sight and communication relays).
- $\text{TPI} < 0$: Depressions, crater floors, valleys (candidates for Permanently Shadowed Regions [PSRs] containing volatile water ice).

---

### 3. Analog Compatibility Index (ACI)

The Analog Compatibility Index is a normalized terrain-statistics similarity score $[0, 100\%]$ comparing an Earth DEM signature with a target DEM signature. It is not a measure or proof of mission-site suitability.

For each metric $m \in M$, the implementation computes:
$$S_m = \exp \left( - \frac{1}{2} \left( \frac{|v_m^{\text{target}} - v_m^{\text{candidate}}|}{\sigma_m} \right)^2 \right)$$

The code sets $\sigma_m = \max(0.5|v_m^{\text{target}}|, \max(0.3v_m^{\text{target}}, 1))$ for the nonnegative terrain metrics used by ACI.

The base topographic score is:
$$\text{ACI}_{\text{base}} = \frac{ \sum_{m} w_m S_m }{ \sum_m w_m } \times 100$$

The default fixed weights implemented in PTAE are:
- $w_{\text{slope\_mean}} = 0.30$
- $w_{\text{slope\_std}} = 0.15$
- $w_{\text{tri\_mean}} = 0.25$
- $w_{\text{tri\_std}} = 0.15$
- $w_{\text{elevation\_std}} = 0.15$

**Environmental Modifiers:**
The implementation adds an environmental bonus of up to 5 ACI points to the base topographic score. If $n$ of the three Boolean flags are true, the bonus is $\operatorname{round}(5.0 \times n / 3, 2)$ points:
- **Hyper-Aridity:** `is_hyper_arid = true` counts as one matching flag.
- **Basaltic Composition:** `is_basaltic = true` counts as one matching flag.
- **Subterranean Lava Tubes:** `has_lava_tubes = true` counts as one matching flag.

One matching flag adds 1.67 points, two add 3.33 points, and all three add 5.00 points.

The final ACI is capped at 100 for an exact match across all positively weighted metrics; a non-perfect match is capped at 99.99. The environmental bonus is additive, not a multiplicative $(1 + \beta)$ factor.

#### Weight Sensitivity
The separate [weight-sensitivity analysis](../dashboard/weight_sensitivity.json) uses the unchanged 300x300 arrays, prepared-grid resolutions, catalog order, and ACI functions with custom normalized weights. Across 1,018 scenarios (baseline, ten one-at-a-time changes, equal weights, five drop-one cases, 1,000 Dirichlet(1,1,1,1,1) draws with seed 42, and flag bonus off), Teide stays Moon #1 in 945 cases (92.829077%) and top three in all 1,018 (100%); Kilauea stays Mars #1 in 227 (22.298625%) and top three in 431 (42.337917%). Minimum/median Spearman are 0.738346/0.968421 for Moon and -0.004511/0.678947 for Mars, using ordinal positions after the existing ACI/base-score/stable-catalog tie breaks, consistent with window sensitivity. Both full baseline orders and all ACI values are checked against the protected ranking JSONs before writing. The artifact records every leader change, random-only summaries, and its denominator including baseline and bonus-off. This tests robustness to weights, not scientific correctness of the weights or flags; percentages depend on this scenario mix, and existing DEM resolution/footprint mismatches remain.

---

### 4. Geological Grounding of Selected Analogs

1. **Askja & Holuhraun Caldera, Iceland:**
   - *Volcanic context:* Basaltic lava fields and caldera landforms provide qualitative context for studying volcanic terrain. They are not direct validation of lunar mare or lava-tube equivalence.
2. **McMurdo Dry Valleys, Antarctica:**
   - *Cold-desert context:* Exposed soils, aridity, and permafrost make the region relevant to cold-environment field studies. Similarity in these properties does not make its terrain identical to Mars.
3. **Haughton Impact Crater, Devon Island:**
   - *Impact context:* Haughton offers a polar impact-structure field setting for studying impact materials and landforms; it is not a measured match to a specific lunar or Martian site.

### 5. Current Data and Interpretation Limits

The Moon view lists 7 reference regions (4 with qualitative Earth mappings, 3 reference-only). Selecting a region changes the displayed reference, not the scored DEM; ACI scores use the single Artemis south-pole DEM.

The current checked-in results use a 300×300 LRO LOLA lunar target (20 m source resampled to 33.399998 m/pixel), a 300×300 MOLA Jezero target (333.686104 m/pixel), and 20 real AWS Terrain Tiles Earth windows. Each Earth window is 10 km per side, resampled to 300×300 at approximately 33.3–33.5 m/pixel, as recorded in `data_real/*.json`.

The Mars target is about ten times coarser than the Earth candidate grids. Slope, TRI, and other DEM-derived metrics depend on spatial resolution and window scale; the Mars ranking is therefore indicative and not directly comparable to the Earth candidates as a scale-controlled result. The dashboard's ranking values describe terrain-statistics similarity, not mission safety, operational readiness, or site suitability.

For 14 of the 15 added Earth sites, AWS DEMs were upsampled from ~55.5-76.2 m/pixel to ~33 m/pixel; Svalbard was downsampled from 15.65 to 33.34 m/pixel. Upsampling does not add terrain detail. The Mars grid was resampled from ~451 to ~334 m/pixel and spans ~100 km per side, versus ~10 km for Earth windows. Flags on added sites are unverified. DEM metrics check terrain morphology only, not geology.

The new sensitivity analysis covers only center crops of the existing window (no larger windows); mappings for added sites are provisional; the default synthetic demo and legacy `results.json` cover only the original five sites.

The 15 added Earth-site coordinates and Boolean analog flags are approximate catalog metadata and require manual verification. Their qualitative Moon/Mars mappings in `dashboard/target_sites.json` are provisional, based on catalog descriptions, target features, and the existing 10 km DEM metrics; they are separate from ACI. Lonar's catalog description identifies a basalt-hosted impact crater, but its `basaltic` flag remains `false` and unverified; the mapping does not use basalt as a match feature. `dashboard/window_sensitivity.json` retains the historical window study using four synthetic Earth candidates and real Askja/Moon inputs, and adds a separate 20-site real-DEM center-crop analysis for both targets. The crop analysis keeps source pixel resolution fixed while the physical window shrinks; its artifact is separate from the unchanged full-window ranking files. The browser Mission Weight Calculator is a heuristic scenario model, not the Python ACI. The default CLI mode also remains a procedural synthetic demo unless `--use-existing-data --data-dir data_real` is specified.
