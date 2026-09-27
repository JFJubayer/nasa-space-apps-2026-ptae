# NASA Space Apps 2026: Earth Analog Finder

This project provides a programmatic way to identify Earth locations that are topographical analogs to locations on the Moon or Mars. It computes and compares the **Slope** and **Terrain Ruggedness Index (TRI)** from Digital Elevation Models (DEMs).

## 🛠️ Setup Instructions

1. **Install Requirements:**
   Make sure you have Python 3 installed. Create a virtual environment and install the dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Generate Synthetic Data (For Quick Testing):**
   To test the pipeline without downloading gigabytes of real satellite data, you can generate synthetic DEMs (`.npy` files) simulating the Moon, Atacama, Iceland, and Death Valley:
   ```bash
   python generate_synthetic_dems.py
   ```

3. **Visualize the Data:**
   Generate heatmaps showing the Elevation, Slope, and Ruggedness (TRI) for all your datasets. This will save `.png` images in the `data/` folder, which are perfect for your Space Apps presentation!
   ```bash
   python visualize_terrain.py
   ```

4. **Find the Best Analog:**
   Compare the Earth signatures to the Lunar target to find the closest mathematical match:
   ```bash
   python find_analog.py
   ```

## 🌌 Using Real NASA Data

Once you verify the script works, replace the `.npy` arrays with real GeoTIFFs (`.tif`). The script automatically detects `.tif` files and uses `rasterio` to load them!

1.  **Moon Data (LOLA):** Go to the [NASA PDS Geosciences Node](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) or use the [LROC QuickMap](https://quickmap.lroc.asu.edu/) to export a DEM for the Lunar South Pole.
2.  **Earth Data (SRTM):** Go to [NASA Earthdata Search](https://search.earthdata.nasa.gov/) and search for "SRTM". Download GeoTIFFs for potential analog regions.
3.  **Update the Scripts:** Change the filenames in `find_analog.py` and `visualize_terrain.py` to point to your new `.tif` files.

## 🧠 How it Works

1. `compute_terrain_metrics.py` loads the DEMs.
2. It calculates the Slope (steepness) and TRI (ruggedness) across the entire image.
3. It extracts a "Signature" (Mean and Standard Deviation of these metrics).
4. `find_analog.py` calculates the Euclidean distance between the Moon's signature and the Earth candidates' signatures. The candidate with the lowest score is the closest physical match!
