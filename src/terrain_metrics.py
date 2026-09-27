import os
import numpy as np
from scipy.ndimage import generic_filter, uniform_filter

def calculate_slope(dem_array, resolution=30.0):
    """
    Calculate the surface slope in degrees using central differences.
    """
    dy, dx = np.gradient(dem_array, resolution, resolution)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    return np.degrees(slope_rad)

def calculate_aspect(dem_array, resolution=30.0):
    """
    Calculate the aspect (slope direction) in degrees (0-360, with 0=North).
    """
    dy, dx = np.gradient(dem_array, resolution, resolution)
    aspect_rad = np.arctan2(-dx, dy)
    aspect_deg = np.degrees(aspect_rad)
    return np.where(aspect_deg < 0, aspect_deg + 360, aspect_deg)

def calculate_tri(dem_array):
    """
    Calculate Riley's Terrain Ruggedness Index (TRI).
    TRI = sqrt(sum((z_ij - z_center)^2)) over a 3x3 neighbourhood.
    """
    def _tri_kernel(values):
        center = values[4]
        return np.sqrt(np.sum((values - center)**2))
    
    footprint = np.ones((3, 3))
    return generic_filter(dem_array, _tri_kernel, footprint=footprint, mode='reflect')

def calculate_tpi(dem_array, size=5):
    """
    Calculate Topographic Position Index (TPI).
    Difference between central elevation and mean elevation of surrounding cells.
    Positive: ridges / peaks. Negative: valleys / depressions.
    """
    mean_filter = uniform_filter(dem_array, size=size, mode='reflect')
    return dem_array - mean_filter

def load_dem(dem_path, default_resolution=30.0):
    """
    Loads DEM from .npy or .tif. Returns (dem_array, resolution_meters).
    """
    if not os.path.exists(dem_path):
        raise FileNotFoundError(f"DEM file not found: {dem_path}")
        
    if dem_path.endswith('.npy'):
        dem = np.load(dem_path).astype(float)
        return dem, default_resolution
    elif dem_path.endswith(('.tif', '.tiff')):
        try:
            import rasterio
            with rasterio.open(dem_path) as src:
                dem = src.read(1).astype(float)
                nodata = src.nodata
                if nodata is not None:
                    dem[dem == nodata] = np.nan
                res = src.transform[0]
                return dem, abs(res)
        except ImportError:
            raise ImportError("rasterio is required to read GeoTIFF files. Install via pip install rasterio")
    else:
        raise ValueError(f"Unsupported file format: {dem_path}")

def extract_terrain_signature(dem_path, resolution=30.0):
    """
    Extracts comprehensive quantitative topographical metrics from a DEM.
    """
    dem, res = load_dem(dem_path, default_resolution=resolution)
    
    # Filter out NaNs if any
    valid_mask = ~np.isnan(dem)
    valid_dem = dem[valid_mask]
    
    slope = calculate_slope(dem, res)
    tri = calculate_tri(dem)
    tpi = calculate_tpi(dem)
    
    signature = {
        "elevation_mean": float(np.nanmean(dem)),
        "elevation_std": float(np.nanstd(dem)),
        "elevation_min": float(np.nanmin(dem)),
        "elevation_max": float(np.nanmax(dem)),
        "slope_mean": float(np.nanmean(slope)),
        "slope_std": float(np.nanstd(slope)),
        "slope_p90": float(np.nanpercentile(slope, 90)),
        "tri_mean": float(np.nanmean(tri)),
        "tri_std": float(np.nanstd(tri)),
        "tri_max": float(np.nanmax(tri)),
        "tpi_std": float(np.nanstd(tpi)),
        "resolution_m": float(res)
    }
    return signature, dem, slope, tri
