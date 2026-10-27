#!/usr/bin/env python3
"""Fetch AWS Terrain Tiles windows for the sites catalog and prepare PTAE DEMs."""

import argparse
import json
import math
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_CATALOG = PROJECT_ROOT / "data" / "sites.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data_real"
AWS_TERRAIN_TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{zoom}/{x}/{y}.tif"
WEB_MERCATOR_HALF_WORLD = 20037508.342789244
USER_AGENT = "PTAE DEM fetcher (AWS Terrain Tiles)"
SITE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]*$")


def load_sites(catalog_path):
    """Load and minimally validate the Earth site records used by this command."""
    with Path(catalog_path).open(encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    sites = catalog.get("sites") if isinstance(catalog, dict) else None
    if not isinstance(sites, list) or not sites:
        raise ValueError("Site catalog must contain a non-empty 'sites' list.")

    site_ids = set()
    for site in sites:
        if not isinstance(site, dict):
            raise ValueError("Each site record must be an object.")
        site_id = site.get("site_id")
        if not isinstance(site_id, str) or not SITE_ID_PATTERN.fullmatch(site_id):
            raise ValueError(f"Invalid site_id: {site_id!r}")
        if site_id in site_ids:
            raise ValueError(f"Duplicate site_id: {site_id}")
        site_ids.add(site_id)
        for field in ("name", "country", "lat", "lon", "window_km"):
            if field not in site:
                raise ValueError(f"Site '{site_id}' is missing required field '{field}'.")
        if isinstance(site["lat"], bool) or not isinstance(site["lat"], (int, float)) or not -90 <= site["lat"] <= 90:
            raise ValueError(f"Site '{site_id}' has an invalid latitude.")
        if isinstance(site["lon"], bool) or not isinstance(site["lon"], (int, float)) or not -180 <= site["lon"] <= 180:
            raise ValueError(f"Site '{site_id}' has an invalid longitude.")
        if isinstance(site["window_km"], bool) or not isinstance(site["window_km"], (int, float)) or site["window_km"] <= 0:
            raise ValueError(f"Site '{site_id}' has an invalid window_km.")
    return sites


def tile_indices_for_window(latitude, longitude, window_km, zoom=10):
    """Return slippy-map tile indices covering a ground-sized square at a site."""
    if not -85.05112878 < latitude < 85.05112878:
        raise ValueError("AWS Web Mercator tiles do not cover latitudes beyond +/-85.0511 degrees.")
    tile_count = 2 ** zoom
    tile_span = (2 * WEB_MERCATOR_HALF_WORLD) / tile_count
    projected_x = math.radians(longitude) * 6378137.0
    projected_y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2))
    ground_scale = max(math.cos(math.radians(latitude)), 1e-6)
    projected_half_window = window_km * 500 / ground_scale

    first_x = math.floor((projected_x - projected_half_window + WEB_MERCATOR_HALF_WORLD) / tile_span)
    last_x = math.floor((projected_x + projected_half_window + WEB_MERCATOR_HALF_WORLD) / tile_span)
    first_y = math.floor((WEB_MERCATOR_HALF_WORLD - (projected_y + projected_half_window)) / tile_span)
    last_y = math.floor((WEB_MERCATOR_HALF_WORLD - (projected_y - projected_half_window)) / tile_span)

    return [
        (x % tile_count, y)
        for y in range(max(0, first_y), min(tile_count - 1, last_y) + 1)
        for x in range(first_x, last_x + 1)
    ]


def _download_tile(zoom, x, y, target_path, timeout):
    url = AWS_TERRAIN_TILE_URL.format(zoom=zoom, x=x, y=y)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response, Path(target_path).open("wb") as output:
        output.write(response.read())

    try:
        import rasterio

        with rasterio.open(target_path) as tile:
            if tile.driver != "GTiff" or tile.count < 1 or tile.crs is None:
                raise ValueError("response is not a georeferenced GeoTIFF")
    except Exception as exc:
        Path(target_path).unlink(missing_ok=True)
        raise ValueError(f"Invalid AWS Terrain Tile {zoom}/{x}/{y}: {exc}") from exc
    return url


def _existing_aws_output(dem_path, sidecar_path):
    if not dem_path.is_file() or not sidecar_path.is_file():
        return False
    try:
        with sidecar_path.open(encoding="utf-8") as sidecar_file:
            metadata = json.load(sidecar_file)
        array = np.load(dem_path, mmap_mode="r")
        return (
            metadata.get("source_dataset", "").startswith("AWS Terrain Tiles")
            and array.shape == (300, 300)
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def fetch_site_dem(site, output_dir, zoom=10, timeout=30):
    """Fetch, mosaic, and prepare one site's terrain window."""
    try:
        import rasterio
        from rasterio.merge import merge
    except ImportError as exc:
        raise RuntimeError("Install rasterio to fetch and prepare GeoTIFF DEM tiles.") from exc

    from scripts.prepare_real_data import prepare_geotiff

    site_id = site["site_id"]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dem = output_dir / f"earth_{site_id}.npy"
    output_sidecar = output_dem.with_suffix(".json")
    if _existing_aws_output(output_dem, output_sidecar):
        return "skipped", output_dem

    tile_indices = tile_indices_for_window(
        float(site["lat"]), float(site["lon"]), float(site["window_km"]), zoom
    )
    if not tile_indices:
        raise ValueError("No AWS tiles intersect the requested window.")

    with tempfile.TemporaryDirectory(prefix=f"ptae-{site_id}-", dir=output_dir) as temp_dir:
        temp_path = Path(temp_dir)
        tile_paths = []
        tile_urls = []
        for x, y in tile_indices:
            tile_path = temp_path / f"tile-{zoom}-{x}-{y}.tif"
            tile_urls.append(_download_tile(zoom, x, y, tile_path, timeout))
            tile_paths.append(tile_path)

        mosaic, transform = merge([str(path) for path in tile_paths])
        with rasterio.open(tile_paths[0]) as first_tile:
            profile = first_tile.profile.copy()
        profile.update(
            driver="GTiff",
            width=mosaic.shape[2],
            height=mosaic.shape[1],
            transform=transform,
            count=mosaic.shape[0],
            compress="deflate",
        )
        mosaic_path = temp_path / "aws_terrain_tiles_mosaic.tif"
        with rasterio.open(mosaic_path, "w", **profile) as mosaic_file:
            mosaic_file.write(mosaic)

        prepared_dir = temp_path / "prepared"
        prepared_dir.mkdir()
        prepared_dem, prepared_sidecar = prepare_geotiff(
            mosaic_path,
            site="iceland",
            source_dataset=f"AWS Terrain Tiles GeoTIFF (zoom {zoom})",
            size=300,
            output_dir=prepared_dir,
            window_km=float(site["window_km"]),
            center_lat=float(site["lat"]),
            center_lon=float(site["lon"]),
        )
        with Path(prepared_sidecar).open(encoding="utf-8") as sidecar_file:
            metadata = json.load(sidecar_file)
        metadata.update({
            "site_id": site_id,
            "source_tile_zoom": zoom,
            "source_tile_urls": tile_urls,
            "coordinate_verification_required": site.get("verify_coordinates_manually", True),
        })
        with Path(prepared_sidecar).open("w", encoding="utf-8") as sidecar_file:
            json.dump(metadata, sidecar_file, indent=2)
            sidecar_file.write("\n")

        os.replace(prepared_dem, output_dem)
        os.replace(prepared_sidecar, output_sidecar)
    return "success", output_dem


def run(catalog_path=DEFAULT_CATALOG, output_dir=DEFAULT_OUTPUT_DIR, zoom=10, timeout=30, site_id=None):
    """Fetch each catalog site independently and print a completion summary."""
    sites = load_sites(catalog_path)
    if site_id:
        sites = [site for site in sites if site["site_id"] == site_id]
        if not sites:
            raise ValueError(f"Site not found in catalog: {site_id}")

    results = []
    for site in sites:
        try:
            status, output_path = fetch_site_dem(site, output_dir, zoom=zoom, timeout=timeout)
            results.append((site["site_id"], status, str(output_path), ""))
        except (OSError, RuntimeError, TimeoutError, urllib.error.URLError, ValueError) as exc:
            results.append((site["site_id"], "failed", "", str(exc)))

    print(f"{'SITE ID':<30} {'STATUS':<10} {'OUTPUT / ERROR'}")
    print("-" * 100)
    for site_id, status, output_path, error in results:
        print(f"{site_id:<30} {status:<10} {output_path or error}")
    counts = {status: sum(result[1] == status for result in results) for status in ("success", "skipped", "failed")}
    print("-" * 100)
    print(f"Total: {len(results)} | succeeded: {counts['success']} | skipped: {counts['skipped']} | failed: {counts['failed']}")
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG, help="Site catalog JSON (default: data/sites.json)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory (default: data_real)")
    parser.add_argument("--zoom", type=int, default=10, help="AWS Terrain Tiles zoom level (default: 10)")
    parser.add_argument("--timeout", type=int, default=30, help="Per-tile network timeout in seconds")
    parser.add_argument("--site-id", help="Fetch only this site ID")
    args = parser.parse_args(argv)
    if args.zoom < 0 or args.zoom > 18:
        parser.error("--zoom must be between 0 and 18")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    try:
        results = run(args.catalog, args.output_dir, args.zoom, args.timeout, args.site_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 1 if any(status == "failed" for _, status, _, _ in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
