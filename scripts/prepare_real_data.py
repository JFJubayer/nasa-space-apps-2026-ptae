#!/usr/bin/env python3
"""Resize a source GeoTIFF DEM into a PTAE .npy input and metadata sidecar."""

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np

SITE_OUTPUTS = {
    "moon": "target_moon_artemis_south_pole.npy",
    "mars": "target_mars_jezero_crater.npy",
    "iceland": "earth_iceland_askja.npy",
    "atacama": "earth_atacama_puna.npy",
    "mcmurdo": "earth_mcmurdo_dry_valleys.npy",
    "haughton": "earth_haughton_crater.npy",
    "hawaii": "earth_hawaii_mauna_kea.npy",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _ellipsoid_parameters(crs):
    match = re.search(
        r'(?:SPHEROID|ELLIPSOID)\s*\[\s*"[^"]+"\s*,\s*([\d.eE+-]+)\s*,\s*([\d.eE+-]+)',
        crs.to_wkt(),
        re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"Could not read ellipsoid parameters from CRS: {crs}")
    return float(match.group(1)), float(match.group(2))


def _geocentric_point(longitude, latitude, semi_major_axis, inverse_flattening):
    flattening = 0.0 if inverse_flattening == 0 else 1.0 / inverse_flattening
    eccentricity_squared = flattening * (2.0 - flattening)
    longitude = math.radians(longitude)
    latitude = math.radians(latitude)
    normal_radius = semi_major_axis / math.sqrt(
        1.0 - eccentricity_squared * math.sin(latitude) ** 2
    )
    return np.array((
        normal_radius * math.cos(latitude) * math.cos(longitude),
        normal_radius * math.cos(latitude) * math.sin(longitude),
        normal_radius * (1.0 - eccentricity_squared) * math.sin(latitude),
    ))


def _resolution_m_per_pixel(dataset, row, col):
    if dataset.crs is None:
        raise ValueError("GeoTIFF must define a CRS to calculate resolution in meters per pixel")

    transform = dataset.transform
    points = [
        transform @ (col, row),
        transform @ (col + 1, row),
        transform @ (col, row + 1),
    ]
    from rasterio.warp import transform as reproject

    geodetic_crs = dataset.crs.geodetic_crs
    x_coords, y_coords = reproject(
        dataset.crs,
        geodetic_crs,
        [point[0] for point in points],
        [point[1] for point in points],
    )
    semi_major_axis, inverse_flattening = _ellipsoid_parameters(geodetic_crs)
    ground_points = [
        _geocentric_point(longitude, latitude, semi_major_axis, inverse_flattening)
        for longitude, latitude in zip(x_coords, y_coords)
    ]
    x_resolution = float(np.linalg.norm(ground_points[1] - ground_points[0]))
    y_resolution = float(np.linalg.norm(ground_points[2] - ground_points[0]))
    if not math.isfinite(x_resolution) or not math.isfinite(y_resolution):
        raise ValueError("Could not calculate ground resolution for the GeoTIFF CRS")
    return x_resolution, y_resolution


def _center_lat_lon(dataset, window):
    from rasterio.warp import transform
    from rasterio.windows import bounds

    left, bottom, right, top = bounds(window, dataset.transform)
    center_x = (left + right) / 2
    center_y = (bottom + top) / 2
    try:
        longitudes, latitudes = transform(dataset.crs, dataset.crs.geodetic_crs, [center_x], [center_y])
        return latitudes[0], longitudes[0]
    except Exception:
        return None, None


def _crop_window(dataset, window_km, center_lat, center_lon):
    from rasterio.windows import Window
    from rasterio.warp import transform

    if window_km is None:
        if center_lat is not None or center_lon is not None:
            raise ValueError("--center-lat and --center-lon require --window-km")
        return Window(0, 0, dataset.width, dataset.height), None
    if window_km <= 0:
        raise ValueError("window_km must be a positive number")
    if center_lat is None or center_lon is None:
        raise ValueError("--window-km requires both --center-lat and --center-lon")
    if not -90 <= center_lat <= 90 or not -180 <= center_lon <= 180:
        raise ValueError("Center latitude/longitude must be within valid degree ranges")

    try:
        x_coords, y_coords = transform(
            dataset.crs.geodetic_crs, dataset.crs, [center_lon], [center_lat]
        )
    except Exception as exc:
        raise ValueError(f"Could not transform the requested center into raster CRS: {exc}") from exc
    center_x, center_y = x_coords[0], y_coords[0]
    center_col, center_row = (~dataset.transform) @ (center_x, center_y)
    x_resolution, y_resolution = _resolution_m_per_pixel(dataset, center_row, center_col)
    width = max(1, math.ceil(window_km * 1000 / x_resolution))
    height = max(1, math.ceil(window_km * 1000 / y_resolution))
    col_offset = math.floor(center_col - width / 2)
    row_offset = math.floor(center_row - height / 2)

    if (
        col_offset < 0 or row_offset < 0
        or col_offset + width > dataset.width
        or row_offset + height > dataset.height
    ):
        raise ValueError(
            f"Requested {window_km:g} km window centered at ({center_lat:g}, {center_lon:g}) "
            "extends outside the raster bounds"
        )

    return Window(col_offset, row_offset, width, height), (center_lat, center_lon)


def prepare_geotiff(
    input_path,
    site,
    source_dataset,
    size=300,
    output_dir=None,
    window_km=None,
    center_lat=None,
    center_lon=None,
):
    """Resample a GeoTIFF to a square NumPy DEM and write its source metadata."""
    try:
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.fill import fillnodata
    except ImportError as exc:
        raise ImportError("Install rasterio with `python -m pip install rasterio`.") from exc

    if site not in SITE_OUTPUTS:
        raise ValueError(f"Unknown site '{site}'. Choose from: {', '.join(SITE_OUTPUTS)}")
    if size <= 0:
        raise ValueError("size must be a positive integer")
    if not source_dataset.strip():
        raise ValueError("source_dataset must not be empty")

    input_path = Path(input_path)
    output_dir = Path(output_dir) if output_dir else PROJECT_ROOT / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / SITE_OUTPUTS[site]
    sidecar_path = output_path.with_suffix(".json")

    with rasterio.open(input_path) as dataset:
        if dataset.driver != "GTiff" or dataset.count < 1:
            raise ValueError(f"Input is not a valid GeoTIFF DEM: {input_path}")

        window, requested_center = _crop_window(dataset, window_km, center_lat, center_lon)
        from rasterio.windows import bounds as window_bounds

        left, bottom, right, top = window_bounds(window, dataset.transform)
        center_col = window.col_off + window.width / 2
        center_row = window.row_off + window.height / 2
        original_x_resolution, original_y_resolution = _resolution_m_per_pixel(
            dataset, center_row, center_col
        )
        output_x_resolution = original_x_resolution * window.width / size
        output_y_resolution = original_y_resolution * window.height / size
        if requested_center:
            output_center_lat, output_center_lon = requested_center
        else:
            output_center_lat, output_center_lon = _center_lat_lon(dataset, window)

        resampled = dataset.read(
            1,
            window=window,
            out_shape=(size, size),
            masked=True,
            resampling=Resampling.bilinear,
        ).astype(np.float32)
        invalid = np.ma.getmaskarray(resampled) | ~np.isfinite(np.ma.getdata(resampled))
        if invalid.all():
            raise ValueError(f"GeoTIFF contains no valid elevation cells: {input_path}")
        if invalid.any():
            valid_mask = (~invalid).astype(np.uint8)
            values = np.asarray(np.ma.getdata(resampled), dtype=np.float32).copy()
            values[invalid] = 0.0
            resampled = fillnodata(
                values,
                mask=valid_mask,
                max_search_distance=max(size * 2, 1),
            )
            if not np.isfinite(resampled).all():
                raise ValueError(f"Could not fill all no-data cells in GeoTIFF: {input_path}")
        else:
            resampled = np.asarray(np.ma.getdata(resampled), dtype=np.float32)

        metadata = {
            "source_file": input_path.name,
            "source_dataset": source_dataset,
            "original_ground_resolution_m_per_pixel": round(
                math.sqrt(original_x_resolution * original_y_resolution), 6
            ),
            "output_ground_resolution_m_per_pixel": round(
                math.sqrt(output_x_resolution * output_y_resolution), 6
            ),
            "original_ground_resolution_axes_m_per_pixel": {
                "x": round(original_x_resolution, 6),
                "y": round(original_y_resolution, 6),
            },
            "output_ground_resolution_axes_m_per_pixel": {
                "x": round(output_x_resolution, 6),
                "y": round(output_y_resolution, 6),
            },
            "center_lat": output_center_lat,
            "center_lon": output_center_lon,
            "bounds": {
                "left": left,
                "bottom": bottom,
                "right": right,
                "top": top,
                "crs": dataset.crs.to_string(),
            },
            "output_size": [size, size],
            "resampling": "bilinear",
        }

    np.save(output_path, resampled)
    with sidecar_path.open("w", encoding="utf-8") as sidecar:
        json.dump(metadata, sidecar, indent=2)
        sidecar.write("\n")
    return output_path, sidecar_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Source GeoTIFF DEM")
    parser.add_argument("--site", choices=tuple(SITE_OUTPUTS), required=True)
    parser.add_argument("--source-dataset", required=True, help="Dataset/product name for the sidecar")
    parser.add_argument("--size", type=int, default=300, help="Square output width and height (default: 300)")
    parser.add_argument("--window-km", type=float, help="Crop a window of this ground width and height around a point")
    parser.add_argument("--center-lat", type=float, help="Crop center latitude in degrees; requires --window-km")
    parser.add_argument("--center-lon", type=float, help="Crop center longitude in degrees; requires --window-km")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data")
    args = parser.parse_args(argv)

    try:
        output_path, sidecar_path = prepare_geotiff(
            args.input,
            args.site,
            args.source_dataset,
            size=args.size,
            output_dir=args.output_dir,
            window_km=args.window_km,
            center_lat=args.center_lat,
            center_lon=args.center_lon,
        )
    except (ImportError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Prepared DEM: {output_path}")
    print(f"Metadata:     {sidecar_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())