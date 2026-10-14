#!/usr/bin/env python3
"""
NASA Space Apps Challenge 2026
Automated Data Downloader for Real NASA / USGS Sample GeoTIFFs

Downloads curated Cloud-Optimized GeoTIFF (COG) subsets from NASA PDS and USGS.
"""

import argparse
import math
import os
import sys
import tempfile
import urllib.error
import urllib.request

# Curated public GeoTIFF DEM endpoints (no authentication required).
SAMPLE_SOURCES = {
    "moon": {
        "filename": "luna_south_pole_lola_window.tif",
        "dataset": "LRO LOLA South Polar DEM (80-90S)",
        "description": "South Pole, Moon (20 m/pixel; remote window required)",
        "url": "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF",
        "approx_size_mb": 2570,
    },
    "mars": {
        "filename": "mars_mola_global_463m.tif",
        "dataset": "MGS MOLA global DEM",
        "description": "Global Mars elevation DEM (463 m/pixel)",
        "url": "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
        "approx_size_mb": 60,
    },
    "iceland": {
        "filename": "earth_iceland_askja_srtm.tif",
        "dataset": "SRTM 1 arc-second elevation tile",
        "description": "Askja Caldera, Iceland (approximately 30 m/pixel)",
        "url": "https://s3.amazonaws.com/elevation-tiles-prod/geotiff/10/464/266.tif",
        "approx_size_mb": 15,
    },
}

TIMEOUT_SECONDS = 60
CHUNK_SIZE = 1024 * 1024
MAX_FULL_DOWNLOAD_BYTES = 500 * 1024 * 1024
MAX_WINDOW_KM = 100.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


def _print_response_info(response):
    headers = response.headers
    print(f"HTTP status: {response.status}")
    print(f"Final URL: {response.geturl()}")
    print(f"Content-Type: {headers.get('Content-Type', '(not provided)')}")
    print(f"Content-Length: {headers.get('Content-Length', '(not provided)')}")


def _log_http_error(error):
    print(f"HTTP status: {error.code} {error.reason}", file=sys.stderr)
    print(f"Final URL: {error.geturl()}", file=sys.stderr)
    print("Response headers:", file=sys.stderr)
    for name, value in error.headers.items():
        print(f"  {name}: {value}", file=sys.stderr)
    content_type = error.headers.get("Content-Type", "").lower()
    if "text/html" in content_type or "text/plain" in content_type:
        preview = error.read(200)
        print(f"First 200 response bytes: {preview!r}", file=sys.stderr)


def _open_url(url, site, method="GET", extra_headers=None):
    attempts = 2 if site == "mars" else 1
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)

    for attempt in range(attempts):
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            if attempt + 1 < attempts:
                print(f"HTTP {exc.code} for {site}; retrying once...", file=sys.stderr)
                exc.close()
                continue
            _log_http_error(exc)
            raise RuntimeError(f"HTTP {exc.code} {exc.reason} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt + 1 < attempts:
                print(f"Request failed for {site}; retrying once: {exc}", file=sys.stderr)
                continue
            raise RuntimeError(f"Request failed for {url}: {exc}") from exc


def _is_text_response(content_type, first_bytes=b""):
    if "text/html" in content_type.lower() or "text/plain" in content_type.lower():
        return True
    return first_bytes.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<?xml"))


def _print_html_preview(url, site):
    try:
        with _open_url(url, site, extra_headers={"Range": "bytes=0-199"}) as response:
            print(f"First 200 response bytes: {response.read(200)!r}")
    except Exception as exc:
        print(f"Could not read response preview: {exc}", file=sys.stderr)


def _validate_geotiff(path, site):
    try:
        import rasterio

        with rasterio.open(path) as dataset:
            if dataset.driver != "GTiff" or dataset.count < 1:
                raise ValueError("response is not a GeoTIFF raster")
    except Exception as exc:
        raise ValueError(f"Download for '{site}' was not a valid GeoTIFF: {exc}") from exc


def _download_window(info, target_path, window_km):
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError as exc:
        raise RuntimeError("Install rasterio with `python -m pip install rasterio`.") from exc

    if not 0 < window_km <= MAX_WINDOW_KM:
        raise ValueError(f"--window-km must be greater than 0 and at most {MAX_WINDOW_KM:g}")

    remote_path = "/vsicurl/" + info["url"]
    temp_path = None
    try:
        print(f"Reading a centered {window_km:g} km window from the remote LOLA COG; the full file will not be downloaded.")
        with rasterio.Env(
            GDAL_HTTP_USERAGENT=USER_AGENT,
            GDAL_HTTP_TIMEOUT=str(TIMEOUT_SECONDS),
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        ):
            with rasterio.open(remote_path) as dataset:
                if dataset.driver != "GTiff" or not dataset.crs or not dataset.crs.is_projected:
                    raise ValueError("Remote Moon source must be a projected GeoTIFF")
                unit_factor = dataset.crs.linear_units_factor[1]
                transform = dataset.transform
                x_resolution = math.hypot(transform.a, transform.d) * unit_factor
                y_resolution = math.hypot(transform.b, transform.e) * unit_factor
                width = min(dataset.width, max(1, round(window_km * 1000 / x_resolution)))
                height = min(dataset.height, max(1, round(window_km * 1000 / y_resolution)))
                window = Window(
                    (dataset.width - width) // 2,
                    (dataset.height - height) // 2,
                    width,
                    height,
                )
                dem = dataset.read(window=window)
                profile = dataset.profile.copy()
                profile.update(
                    driver="GTiff",
                    width=width,
                    height=height,
                    transform=dataset.window_transform(window),
                    compress="deflate",
                    tiled=False,
                )

                with tempfile.NamedTemporaryFile(
                    prefix=".ptae-download-", suffix=".part", dir=os.path.dirname(target_path), delete=False
                ) as temp_file:
                    temp_path = temp_file.name
                with rasterio.open(temp_path, "w", **profile) as output:
                    output.write(dem)

        _validate_geotiff(temp_path, "moon")
        os.replace(temp_path, target_path)
        temp_path = None
        print(f"Saved {width}x{height} pixel window to {target_path}")
        return target_path
    except Exception as exc:
        raise RuntimeError(f"Could not read the remote Moon window: {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def download_file(site, target_dir, window_km=None):
    """Download a selected GeoTIFF sample, validating it before saving."""
    if site not in SAMPLE_SOURCES:
        raise ValueError(f"Unknown site '{site}'. Choose from: {', '.join(SAMPLE_SOURCES)}")
    if window_km is not None and site != "moon":
        raise ValueError("--window-km is currently supported only for the Moon LOLA sample")

    info = SAMPLE_SOURCES[site]
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, info["filename"])
    temp_path = None
    try:
        print(f"Downloading {info['dataset']} for {site}: {info['description']}")
        print(f"Source: {info['url']}")
        with _open_url(info["url"], site, method="HEAD") as response:
            _print_response_info(response)
            head_content_type = response.headers.get("Content-Type", "")
            content_length = int(response.headers.get("Content-Length") or 0)
            accept_ranges = response.headers.get("Accept-Ranges", "").lower()
            final_url = response.geturl()

        if "text/html" in head_content_type.lower() or "text/plain" in head_content_type.lower():
            _print_html_preview(final_url, site)
            raise ValueError(f"URL for '{site}' returned {head_content_type}, not a GeoTIFF")

        if site == "moon":
            if window_km is None and (content_length == 0 or content_length > MAX_FULL_DOWNLOAD_BYTES):
                size_text = (
                    f"{content_length:,} bytes ({content_length / (1024 * 1024):.1f} MiB)"
                    if content_length
                    else "an unknown size"
                )
                raise ValueError(
                    f"The Moon GeoTIFF is {size_text}; "
                    "refusing a full download. Specify --window-km (maximum 100) to read "
                    "a centered window through rasterio /vsicurl/."
                )
            if window_km is not None:
                if accept_ranges != "bytes":
                    raise ValueError("Moon GeoTIFF does not advertise byte-range access for remote window reads")
                return _download_window(info, target_path, window_km)

        with _open_url(info["url"], site) as response:
            _print_response_info(response)
            content_type = response.headers.get("Content-Type", "")
            first_chunk = response.read(200)
            if _is_text_response(content_type, first_chunk):
                print(f"First 200 response bytes: {first_chunk!r}")
                raise ValueError(f"URL for '{site}' returned text, not a GeoTIFF")

            with tempfile.NamedTemporaryFile(
                prefix=".ptae-download-", suffix=".part", dir=target_dir, delete=False
            ) as temp_file:
                temp_path = temp_file.name
            with open(temp_path, "wb") as output_file:
                output_file.write(first_chunk)
                total_size = int(response.headers.get("Content-Length") or 0)
                downloaded = len(first_chunk)
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    output_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        progress = min(downloaded * 100 / total_size, 100.0)
                        message = f"Progress: {progress:.1f}% ({downloaded / 1048576:.1f} MB)"
                    else:
                        message = f"Downloaded {downloaded / 1048576:.1f} MB"
                    sys.stdout.write(f"\r{message}")
                    sys.stdout.flush()

        print()
        _validate_geotiff(temp_path, site)
        os.replace(temp_path, target_path)
        temp_path = None
        print(f"Download complete: {target_path}")
        return target_path
    except Exception as exc:
        raise RuntimeError(f"Download failed for '{site}': {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download a public planetary/Earth DEM sample")
    parser.add_argument("--site", choices=tuple(SAMPLE_SOURCES), required=True)
    parser.add_argument(
        "--window-km",
        type=float,
        help="Read a centered Moon LOLA COG window in km (required to avoid its full multi-GB download)",
    )
    args = parser.parse_args(argv)

    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    try:
        download_file(args.site, target_dir, window_km=args.window_km)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
