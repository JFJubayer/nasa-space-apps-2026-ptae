import os
import numpy as np

def create_crater(dem, center_x, center_y, radius, depth):
    """Adds a realistic bowl-shaped impact crater with raised rim and ejecta blanket."""
    y, x = np.ogrid[:dem.shape[0], :dem.shape[1]]
    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    
    # Crater cavity
    inner_mask = dist <= radius
    dem[inner_mask] -= depth * (1.0 - (dist[inner_mask] / radius)**2)
    
    # Raised rim
    rim_outer = radius * 1.3
    rim_mask = (dist > radius) & (dist <= rim_outer)
    rim_height = depth * 0.22
    dem[rim_mask] += rim_height * (1.0 - (dist[rim_mask] - radius) / (rim_outer - radius))
    
    # Ejecta decay
    ejecta_outer = radius * 2.2
    ejecta_mask = (dist > rim_outer) & (dist <= ejecta_outer)
    dem[ejecta_mask] += (rim_height * 0.4) * (1.0 - (dist[ejecta_mask] - rim_outer) / (ejecta_outer - rim_outer))
    
    return dem

def generate_lunar_south_pole(size=300, seed=42):
    """Simulates Lunar South Pole (Shackleton / Malapert region)."""
    np.random.seed(seed)
    # Rugged highland terrain with micro-roughness
    dem = np.random.normal(loc=-1200, scale=35, size=(size, size))
    # Massive regional impact ridge
    y, x = np.ogrid[:size, :size]
    dem += 400.0 * np.sin(x / 40.0) * np.cos(y / 60.0)
    
    # Major primary crater (simulating Shackleton)
    dem = create_crater(dem, size // 2, size // 2, radius=size // 4, depth=600)
    
    # Secondary impact craters
    for _ in range(35):
        cx, cy = np.random.randint(0, size, 2)
        r = np.random.randint(8, size // 8)
        d = np.random.randint(30, 180)
        dem = create_crater(dem, cx, cy, r, d)
    return dem

def generate_mars_jezero(size=300, seed=101):
    """Simulates Mars Jezero Crater with river delta fan and crater rim."""
    np.random.seed(seed)
    # Smooth floor with wind-blown ripples
    dem = np.random.normal(loc=-2500, scale=8, size=(size, size))
    
    # Jezero crater wall (outer circle). Use mgrid (full arrays) since x/y
    # are boolean-indexed below and ogrid's broadcastable shapes don't survive that.
    y, x = np.mgrid[:size, :size]
    dist_rim = np.sqrt((x - size // 2)**2 + (y - size // 2)**2)
    dem[dist_rim > size * 0.4] += 500 * (dist_rim[dist_rim > size * 0.4] - size * 0.4) / (size * 0.2)
    
    # Delta deposit fan
    delta_mask = (x > size * 0.2) & (x < size * 0.5) & (y > size * 0.3) & (y < size * 0.7)
    dem[delta_mask] += 120.0 * (1.0 - np.sqrt((x[delta_mask] - size * 0.35)**2 + (y[delta_mask] - size * 0.5)**2) / 60.0)
    
    # Aeolian sand dunes & small degraded craters
    for _ in range(12):
        cx, cy = np.random.randint(0, size, 2)
        r = np.random.randint(10, 25)
        d = np.random.randint(20, 60)
        dem = create_crater(dem, cx, cy, r, d)
    return dem

def generate_iceland_askja(size=300, seed=7):
    """Simulates Askja/Holuhraun volcanic caldera and basalt field in Iceland."""
    np.random.seed(seed)
    dem = np.random.normal(loc=650, scale=20, size=(size, size))
    # Caldera collapse structure (looks like a crater)
    dem = create_crater(dem, size // 2, size // 2, radius=size // 5, depth=250)
    # Basaltic lava flow ridges
    y, x = np.ogrid[:size, :size]
    dem += 40.0 * np.cos((x + y) / 15.0)
    # Spatter cones and fissure features
    for _ in range(15):
        cx, cy = np.random.randint(0, size, 2)
        r = np.random.randint(6, 18)
        d = np.random.randint(15, 50)
        dem = create_crater(dem, cx, cy, r, d)
    return dem

def generate_atacama_puna(size=300, seed=13):
    """Simulates Atacama high desert plateau (Puna de Atacama)."""
    np.random.seed(seed)
    dem = np.random.normal(loc=4200, scale=12, size=(size, size))
    # Long gentle alluvial slope
    x = np.linspace(0, 300, size)
    dem += np.tile(x, (size, 1))
    return dem

def generate_mcmurdo_dry_valleys(size=300, seed=29):
    """Simulates McMurdo Dry Valleys, Antarctica (hyper-arid polar desert)."""
    np.random.seed(seed)
    dem = np.random.normal(loc=350, scale=22, size=(size, size))
    # Steep valley walls created by ancient glaciers
    y, _ = np.ogrid[:size, :size]
    dem += 450.0 * (np.abs(y - size // 2) / (size // 2))**1.5
    return dem

def generate_haughton_crater(size=300, seed=55):
    """Simulates Haughton Impact Crater on Devon Island, Canadian Arctic."""
    np.random.seed(seed)
    dem = np.random.normal(loc=200, scale=15, size=(size, size))
    # Central peak rebound + circular impact rim
    dem = create_crater(dem, size // 2, size // 2, radius=size // 3, depth=180)
    # Central peak
    y, x = np.ogrid[:size, :size]
    center_dist = np.sqrt((x - size // 2)**2 + (y - size // 2)**2)
    dem[center_dist <= 25] += 60.0 * (1.0 - center_dist[center_dist <= 25] / 25.0)
    return dem

def generate_hawaii_mauna_kea(size=300, seed=88):
    """Simulates Mauna Kea volcanic cinder cones and basaltic slopes."""
    np.random.seed(seed)
    dem = np.random.normal(loc=3800, scale=10, size=(size, size))
    # Broad shield volcano slope
    y, x = np.ogrid[:size, :size]
    dem += 600.0 * (1.0 - np.sqrt((x - size // 2)**2 + (y - size // 2)**2) / (size // 1.2))
    # Cinder cones
    for _ in range(8):
        cx, cy = np.random.randint(size // 4, 3 * size // 4, 2)
        r = np.random.randint(12, 25)
        d = np.random.randint(30, 70)
        dem = create_crater(dem, cx, cy, r, d)
    return dem

def generate_all_datasets(data_dir="data", size=300, generate=True):
    """Generate datasets or return their paths and metadata without writing them."""
    os.makedirs(data_dir, exist_ok=True)
    
    generators = {
        "target_moon_artemis_south_pole.npy": generate_lunar_south_pole,
        "target_mars_jezero_crater.npy": generate_mars_jezero,
        "earth_iceland_askja.npy": generate_iceland_askja,
        "earth_atacama_puna.npy": generate_atacama_puna,
        "earth_mcmurdo_dry_valleys.npy": generate_mcmurdo_dry_valleys,
        "earth_haughton_crater.npy": generate_haughton_crater,
        "earth_hawaii_mauna_kea.npy": generate_hawaii_mauna_kea
    }
    
    metadata = {
        "earth_iceland_askja": {
            "name": "Askja & Holuhraun Caldera, Iceland",
            "country": "Iceland",
            "lat": 65.03,
            "lon": -16.75,
            "type": "Volcanic / Basaltic Caldera & Lava Tubes",
            "primary_analog_for": "Moon (Artemis Landing Sites)",
            "is_basaltic": True,
            "has_lava_tubes": True,
            "is_hyper_arid": False,
            "description": "Young basaltic lava fields, collapse calderas, and subterranean lava tubes sharing high surface roughness and radiation-shielding morphology with lunar mare."
        },
        "earth_haughton_crater": {
            "name": "Haughton Impact Crater, Devon Island",
            "country": "Canada",
            "lat": 75.38,
            "lon": -89.67,
            "type": "Polar Impact Structure",
            "primary_analog_for": "Moon & Mars (Impact Geology)",
            "is_basaltic": False,
            "has_lava_tubes": False,
            "is_hyper_arid": True,
            "description": "23-km diameter impact crater in high-arctic polar desert. Features shatter cones, polymict impact breccia, and permanently cold ground simulating lunar/martian impactites."
        },
        "earth_mcmurdo_dry_valleys": {
            "name": "McMurdo Dry Valleys",
            "country": "Antarctica",
            "lat": -77.47,
            "lon": 162.27,
            "type": "Hyper-Arid Polar Desert",
            "primary_analog_for": "Mars (Permafrost & Aridity)",
            "is_basaltic": False,
            "has_lava_tubes": False,
            "is_hyper_arid": True,
            "description": "Coldest, driest desert on Earth with katabatic winds, polygon permafrost soils, and extreme subsurface ice stability directly mirroring Martian high-latitude plains."
        },
        "earth_atacama_puna": {
            "name": "Puna de Atacama",
            "country": "Chile / Argentina",
            "lat": -24.50,
            "lon": -68.30,
            "type": "High-Altitude Hyper-Arid Plateau",
            "primary_analog_for": "Mars (UV & Desiccation)",
            "is_basaltic": True,
            "has_lava_tubes": False,
            "is_hyper_arid": True,
            "description": "Hyper-arid high plateau (>4,000m) with high UV-B radiation fluxes, perchlorate-rich saline deposits, and near-zero organic matter simulating Martian surface chemistry."
        },
        "earth_hawaii_mauna_kea": {
            "name": "Mauna Kea Cinder Cones",
            "country": "USA (Hawaii)",
            "lat": 19.82,
            "lon": -155.47,
            "type": "Basaltic Tephra & Pyroclastic Cones",
            "primary_analog_for": "Moon (Lunar Regolith Simulant)",
            "is_basaltic": True,
            "has_lava_tubes": True,
            "is_hyper_arid": False,
            "description": "Sub-alpine basaltic volcanic tephra cones used historically as the reference source for JSC-1A lunar regolith simulant and rover mobility tests."
        }
    }
    
    dataset_files = []
    for filename, gen_fn in generators.items():
        file_path = os.path.join(data_dir, filename)
        if generate:
            arr = gen_fn(size=size)
            np.save(file_path, arr)
        dataset_files.append(file_path)
        
    return dataset_files, metadata
