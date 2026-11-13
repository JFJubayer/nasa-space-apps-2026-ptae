"""Fetch open elevation and climate data and resample it onto local metric grids.

Earth elevation: AWS Terrain Tiles (Terrarium encoding; SRTM/NASADEM/ArcticDEM and other open sources).
Moon elevation: LRO LOLA 20 m south-polar DEM (NASA PGDA, remote COG read).
Mars elevation: MGS MOLA 463 m global DEM mosaic (USGS Astrogeology, remote COG read).
Climate: NASA POWER climatology (T2M, T2M_RANGE, PRECTOTCORR, RH2M, PS).
"""

import json
import math
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from scipy.ndimage import map_coordinates, uniform_filter

EARTH_RADIUS_M = 6371008.8
MARS_RADIUS_M = 3396190.0
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
LOLA_URL = "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF"
MOLA_URL = "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif"
USER_AGENT = "PTAE-NASA-SpaceApps/2.0 (research; open data)"
POWER_PARAMETERS = ("T2M", "T2M_RANGE", "PRECTOTCORR", "RH2M", "PS")


def _session():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(total=4, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504))
    )
    session.mount("https://", adapter)
    session.headers["User-Agent"] = USER_AGENT
    return session


def grid_offsets(width_km, spacing_m):
    """Return metre offsets (east, north) for a square, north-up grid centred on zero."""
    n = int(round(width_km * 1000.0 / spacing_m))
    east = (np.arange(n) - (n - 1) / 2.0) * spacing_m
    north = -east.copy()
    return np.meshgrid(east, north)


def offsets_to_latlon(lat0, lon0, east, north, radius):
    lat = lat0 + np.degrees(north / radius)
    lon = lon0 + np.degrees(east / (radius * np.cos(np.radians(lat))))
    return lat, lon


def _mercator_pixels(lat, lon, zoom):
    scale = 256.0 * 2 ** zoom
    px = (lon + 180.0) / 360.0 * scale
    lat_rad = np.radians(np.clip(lat, -85.05, 85.05))
    py = (1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / math.pi) / 2.0 * scale
    return px, py


def _load_tile(session, zoom, x, y, cache_dir):
    from PIL import Image

    path = os.path.join(cache_dir, "tiles", str(zoom), str(x), f"{y}.png")
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        response = session.get(TILE_URL.format(z=zoom, x=x, y=y), timeout=60)
        response.raise_for_status()
        with open(path, "wb") as handle:
            handle.write(response.content)
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    return rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0


def fetch_earth_dem(lat0, lon0, width_km, spacing_m=120.0, cache_dir="cache", zoom=11):
    """Elevation (m) on a north-up metric grid around (lat0, lon0)."""
    east, north = grid_offsets(width_km, spacing_m)
    lat, lon = offsets_to_latlon(lat0, lon0, east, north, EARTH_RADIUS_M)
    px, py = _mercator_pixels(lat, lon, zoom)
    x_min, x_max = int(px.min() // 256), int(px.max() // 256)
    y_min, y_max = int(py.min() // 256), int(py.max() // 256)

    session = _session()
    coords = [(x, y) for y in range(y_min, y_max + 1) for x in range(x_min, x_max + 1)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tiles = list(pool.map(lambda c: _load_tile(session, zoom, c[0], c[1], cache_dir), coords))
    mosaic = np.zeros(((y_max - y_min + 1) * 256, (x_max - x_min + 1) * 256))
    for (x, y), tile in zip(coords, tiles):
        mosaic[(y - y_min) * 256:(y - y_min + 1) * 256, (x - x_min) * 256:(x - x_min + 1) * 256] = tile
    rows = py - y_min * 256 - 0.5
    cols = px - x_min * 256 - 0.5
    return map_coordinates(mosaic, [rows, cols], order=1, mode="nearest").astype(np.float32)


def _sample_raster(url, xs, ys, block_pixels=1):
    """Bilinear-sample a remote projected raster at projected (x, y) coordinates."""
    import rasterio
    from rasterio.windows import Window

    with rasterio.Env(
        GDAL_HTTP_USERAGENT=USER_AGENT,
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_HTTP_TIMEOUT="120",
        GDAL_HTTP_MAX_RETRY="4",
    ):
        with rasterio.open("/vsicurl/" + url) as dataset:
            inverse = ~dataset.transform
            cols, rows = inverse * (xs, ys)
            pad = 3 + block_pixels
            col0 = max(int(math.floor(cols.min())) - pad, 0)
            row0 = max(int(math.floor(rows.min())) - pad, 0)
            col1 = min(int(math.ceil(cols.max())) + pad, dataset.width)
            row1 = min(int(math.ceil(rows.max())) + pad, dataset.height)
            data = dataset.read(1, window=Window(col0, row0, col1 - col0, row1 - row0), masked=True)
            nodata_fraction = float(np.ma.getmaskarray(data).mean())
            filled = np.ma.filled(data.astype(np.float64), np.nan)
    if np.isnan(filled).any():
        filled = np.where(np.isnan(filled), np.nanmedian(filled), filled)
    if block_pixels > 1:
        filled = uniform_filter(filled, size=block_pixels, mode="nearest")
    values = map_coordinates(filled, [rows - row0 - 0.5, cols - col0 - 0.5], order=1, mode="nearest")
    return values.astype(np.float32), nodata_fraction


def fetch_moon_dem(lat0, lon0, width_km, spacing_m=120.0):
    """LOLA 20 m polar DEM averaged to the common grid spacing; polar-stereographic metres."""
    from pyproj import CRS, Transformer
    import rasterio

    with rasterio.Env(GDAL_HTTP_USERAGENT=USER_AGENT, GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open("/vsicurl/" + LOLA_URL) as dataset:
            crs = CRS.from_wkt(dataset.crs.to_wkt())
            native = abs(dataset.transform.a)
    transformer = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    x0, y0 = transformer.transform(lon0, lat0)
    east, north = grid_offsets(width_km, spacing_m)
    block = max(1, int(round(spacing_m / native)))
    dem, _ = _sample_raster(LOLA_URL, x0 + east, y0 + north, block_pixels=block)
    return dem


def fetch_mars_dem(lat0, lon0, width_km, spacing_m=120.0):
    """MOLA 463 m DEM bilinearly resampled to the common grid spacing."""
    from pyproj import CRS, Transformer
    import rasterio

    with rasterio.Env(GDAL_HTTP_USERAGENT=USER_AGENT, GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open("/vsicurl/" + MOLA_URL) as dataset:
            crs = CRS.from_wkt(dataset.crs.to_wkt())
    transformer = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    east, north = grid_offsets(width_km, spacing_m)
    lat, lon = offsets_to_latlon(lat0, lon0, east, north, MARS_RADIUS_M)
    xs, ys = transformer.transform(lon, lat)
    dem, _ = _sample_raster(MOLA_URL, np.asarray(xs), np.asarray(ys))
    return dem


def fetch_climate(lat, lon, cache_dir="cache"):
    """NASA POWER climatology reduced to the five environment features used for scoring."""
    path = os.path.join(cache_dir, "climate", f"{lat:.3f}_{lon:.3f}.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    response = _session().get(
        POWER_URL,
        params={
            "parameters": ",".join(POWER_PARAMETERS),
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "format": "JSON",
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    annual = {name: values["ANN"] for name, values in payload["properties"]["parameter"].items()}
    climate = {
        "t_mean_c": annual["T2M"],
        "t_daily_range_c": annual["T2M_RANGE"],
        "precip_mm_yr": annual["PRECTOTCORR"] * 365.25,
        "rel_humidity_pct": annual["RH2M"],
        "surface_pressure_kpa": annual["PS"],
        "elevation_m_power": payload["geometry"]["coordinates"][2],
        "source": "NASA POWER climatology, " + payload.get("messages", ["2001-2025"])[0],
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(climate, handle, indent=1)
    return climate
