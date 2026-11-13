"""Multi-baseline terrain statistics used to compare surfaces across bodies and data resolutions.

Slopes are computed as the absolute elevation difference between points separated by a fixed ground
baseline L (the differential-slope approach used for MOLA and LOLA roughness maps; Kreslavsky and Head,
2000; Rosenburg et al., 2011). Using identical physical baselines for every body removes the
resolution mismatch that makes pixel-scale slope statistics incomparable between a 20 m lunar DEM,
a 463 m Mars DEM and a 30 m Earth DEM.
"""

import math

import numpy as np

BASELINES_M = (240, 480, 960, 1920, 3840)


def _differential_slopes(dem, spacing_m, baseline_m):
    k = max(1, int(round(baseline_m / spacing_m)))
    length = k * spacing_m
    # Isotropic: gradient magnitude from the same two-point baseline along rows and columns.
    dx = dem[:-k, k:] - dem[:-k, :-k]
    dy = dem[k:, :-k] - dem[:-k, :-k]
    slopes = np.degrees(np.arctan(np.hypot(dx, dy).ravel() / length))
    return slopes[np.isfinite(slopes)]


def terrain_signature(dem, spacing_m, baselines=BASELINES_M):
    """Median/p90 differential slope per baseline plus relief and the roughness (Hurst) exponent."""
    dem = np.asarray(dem, dtype=np.float64)
    if dem.ndim != 2 or min(dem.shape) < 8:
        raise ValueError("dem must be a 2-D array with at least 8 cells per side")
    usable = [b for b in baselines if max(1, int(round(b / spacing_m))) < min(dem.shape) // 3]
    if not usable:
        raise ValueError("no baseline fits inside the DEM")

    median, p90 = {}, {}
    for baseline in usable:
        slopes = _differential_slopes(dem, spacing_m, baseline)
        median[baseline] = float(np.median(slopes))
        p90[baseline] = float(np.percentile(slopes, 90))

    log_l = np.log(np.array(usable, dtype=float))
    log_s = np.log(np.maximum([median[b] for b in usable], 1e-4))
    hurst = float(np.polyfit(log_l, log_s, 1)[0] + 1.0) if len(usable) > 1 else float("nan")
    low, high = np.nanpercentile(dem, [1, 99])
    return {
        "baselines_m": list(usable),
        "median_slope_deg": [median[b] for b in usable],
        "p90_slope_deg": [p90[b] for b in usable],
        "hurst": hurst,
        "relief_m": float(high - low),
        "elevation_mean_m": float(np.nanmean(dem)),
        "spacing_m": float(spacing_m),
    }


def mask_water(dem, sea_level_m=0.5):
    """Return a copy with cells at or below sea level set to NaN (ocean, large lakes) and the masked fraction."""
    dem = np.asarray(dem, dtype=np.float64)
    water = dem <= sea_level_m
    return np.where(water, np.nan, dem), float(water.mean())


def sliding_windows(region, window_px, stride_px):
    """Yield (row_offset, col_offset, window) covering the region."""
    rows, cols = region.shape
    if window_px > min(rows, cols):
        raise ValueError("window larger than region")
    row_starts = list(range(0, rows - window_px + 1, stride_px))
    col_starts = list(range(0, cols - window_px + 1, stride_px))
    if row_starts[-1] != rows - window_px:
        row_starts.append(rows - window_px)
    if col_starts[-1] != cols - window_px:
        col_starts.append(cols - window_px)
    for row in row_starts:
        for col in col_starts:
            yield row, col, region[row:row + window_px, col:col + window_px]


def window_center_offset_m(region_shape, row, col, window_px, spacing_m):
    """East/north offset (m) of a window centre from the region centre."""
    centre_row = row + (window_px - 1) / 2.0
    centre_col = col + (window_px - 1) / 2.0
    east = (centre_col - (region_shape[1] - 1) / 2.0) * spacing_m
    north = -(centre_row - (region_shape[0] - 1) / 2.0) * spacing_m
    return east, north


def offset_to_latlon(lat0, lon0, east_m, north_m, radius_m=6371008.8):
    lat = lat0 + math.degrees(north_m / radius_m)
    lon = lon0 + math.degrees(east_m / (radius_m * math.cos(math.radians(lat))))
    return lat, lon
