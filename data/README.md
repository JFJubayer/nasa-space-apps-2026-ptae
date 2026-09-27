# Planetary & Terrestrial DEM Data Directory

This directory stores Digital Elevation Models (DEMs) in `.npy` (NumPy arrays) or `.tif` (GeoTIFF) format.

## Procedural Simulation Datasets
When you run `python main.py`, realistic procedural simulations are generated here automatically:
- `target_moon_artemis_south_pole.npy`: Shackleton / Malapert highland terrain with steep crater walls.
- `target_mars_jezero_crater.npy`: Ancient lakebed, delta fan, and crater rim.
- `earth_iceland_askja.npy`: Young basaltic caldera and subterranean lava tubes.
- `earth_mcmurdo_dry_valleys.npy`: Hyper-arid polar desert and frozen polygon ground.
- `earth_atacama_puna.npy`: High-altitude plateau with extreme UV flux.
- `earth_haughton_crater.npy`: Devon Island Arctic impact crater with breccia sheets.
- `earth_hawaii_mauna_kea.npy`: Basaltic tephra cinder cones and regolith simulant.

## Adding Real NASA / ESA GeoTIFFs
To test real mission datasets, simply download GeoTIFFs and place them in this folder:
1. **LRO LOLA (Moon):** [NASA PGDA 5m/pixel LOLA](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/) or [LROC QuickMap](https://quickmap.lroc.asu.edu/)
2. **MGS MOLA (Mars):** [NASA Planetary Data System](https://pds-geosciences.wustl.edu/missions/mgs/mola.htm)
3. **SRTM / ASTER (Earth):** [NASA Earthdata Search](https://search.earthdata.nasa.gov/)

The code will automatically detect and process `.tif` files using `rasterio`!
