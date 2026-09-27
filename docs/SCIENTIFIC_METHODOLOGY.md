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

The Analog Compatibility Index is a normalized similarity score $[0, 100\%]$ evaluating candidate site suitability against a target planetary site.

For each metric $m \in M$:
$$S_m = \exp \left( - \frac{1}{2} \left( \frac{|v_m^{\text{target}} - v_m^{\text{candidate}}|}{\sigma_m} \right)^2 \right)$$

The base topographic score is:
$$\text{ACI}_{\text{base}} = \frac{ \sum_{m} w_m S_m }{ \sum_m w_m } \times 100$$

Where $w_m$ are metric weights tuned to mission profiles:
- $w_{\text{slope\_mean}} = 0.30$
- $w_{\text{slope\_std}} = 0.15$
- $w_{\text{tri\_mean}} = 0.25$
- $w_{\text{tri\_std}} = 0.15$
- $w_{\text{relief\_std}} = 0.15$

**Environmental Modifiers:**
A scalar bonus $(1 + \beta)$ is applied where physical conditions mirror space environments:
- **Hyper-Aridity ($\beta = +0.05$):** Inhibits biological activity, matching lunar/martian sterile regolith.
- **Basaltic Composition ($\beta = +0.05$):** Chemical and abrasive match to lunar mare and martian volcanic plains.
- **Subterranean Lava Tubes ($\beta = +0.05$):** Natural shielding from galactic cosmic rays (GCR), solar particle events (SPE), and micrometeorite impacts.

---

### 4. Geological Grounding of Selected Analogs

1. **Askja & Holuhraun Caldera, Iceland:**
   - *Lunar Analogy:* Formed from basaltic flood lavas with low silica content, closely matching lunar basaltic mare. The sub-glacial and sub-aerial volcanic collapse features provide direct topographic analogues for lunar volcanic grabens and pit craters.
2. **McMurdo Dry Valleys, Antarctica:**
   - *Martian Analogy:* Liquid water is essentially absent; sub-zero temperatures and high katabatic wind speeds mirror the arid, cold martian regime. Ice-cemented ground demonstrates permafrost polygon formation identical to high-latitude martian terrain observed by the Phoenix lander.
3. **Haughton Impact Crater, Devon Island:**
   - *Impact Geology:* Impact cratering is the dominant geomorphological process on the Moon and early Mars. Haughton preserves hydrothermal deposits, impact breccia, and melt sheets in a cold polar desert setting.
