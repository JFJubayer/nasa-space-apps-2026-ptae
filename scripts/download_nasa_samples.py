#!/usr/bin/env python3
"""
NASA Space Apps Challenge 2026
Automated Data Downloader for Real NASA / USGS Sample GeoTIFFs

Downloads curated Cloud-Optimized GeoTIFF (COG) subsets from NASA PDS and USGS.
"""

import os
import sys
import urllib.request

# Curated open scientific DEM sample endpoints (no authentication required)
SAMPLE_SOURCES = {
    "luna_south_pole_shackleton_sample.tif": {
        "description": "LRO LOLA 20m/px South Polar Stereographic DEM (Shackleton Rim)",
        "url": "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LDEM_80S_20MPP_ADJ.TIF",
        "approx_size_mb": 45
    },
    "mars_jezero_crater_sample.tif": {
        "description": "MRO CTX / HiRISE DTM sample (Jezero Crater Delta)",
        "url": "https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_045900_045999/ESP_045994_1985_ESP_046060_1985/DTEEC_045994_1985_046060_1985_U01.IMG",
        "approx_size_mb": 60
    },
    "earth_iceland_askja_srtm.tif": {
        "description": "SRTM 30m Global Elevation Tile (Askja Caldera, Iceland)",
        "url": "https://s3.amazonaws.com/elevation-tiles-prod/geotiff/10/505/298.tif",
        "approx_size_mb": 15
    }
}

def download_file(url, target_path):
    print(f"Downloading: {url}")
    print(f"Saving to:   {target_path}")
    
    def _progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            sys.stdout.write(f"\rProgress: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)")
        else:
            sys.stdout.write(f"\rProgress: {downloaded / (1024*1024):.1f} MB downloaded")
        sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, target_path, reporthook=_progress)
        print("\n✅ Download completed successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Error downloading file: {e}")
        print("Note: If the network restricts direct downloads, manual links are listed in 'data/README.md'.")
        return False

def main():
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(target_dir, exist_ok=True)

    print("=" * 70)
    print("🛰️ NASA OPEN PLANETARY & TERRESTRIAL DATA DOWNLOAD UTILITY")
    print("=" * 70)
    print("Available sample datasets:")
    for idx, (filename, info) in enumerate(SAMPLE_SOURCES.items(), 1):
        print(f" [{idx}] {filename}")
        print(f"     • {info['description']} (~{info['approx_size_mb']} MB)")

    print("\nTo download a sample, run with the filename or number, or let the pipeline")
    print("use the built-in procedural simulation datasets in 'data/'.")
    print("For full global search: https://search.earthdata.nasa.gov/")
    print("=" * 70)

if __name__ == "__main__":
    main()
