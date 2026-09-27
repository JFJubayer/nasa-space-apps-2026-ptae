import numpy as np
import os
from scipy.ndimage import generic_filter

def calculate_slope(dem_array, resolution):
    """
    Calculate the slope of a DEM array in degrees.
    """
    dy, dx = np.gradient(dem_array, resolution, resolution)
    slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
    return slope

def calculate_tri(dem_array):
    """
    Calculate the Terrain Ruggedness Index (TRI).
    """
    def tri_filter(values):
        center = values[4]
        diffs = values - center
        return np.sqrt(np.sum(diffs**2))
    
    footprint = np.ones((3, 3))
    tri = generic_filter(dem_array, tri_filter, footprint=footprint, mode='constant', cval=0.0)
    return tri

def extract_signatures(dem_path):
    """
    Read a DEM file (.tif or .npy) and extract its topographical signature.
    Returns the mean and standard deviation of slope and TRI.
    """
    if dem_path.endswith('.npy'):
        # For our synthetic tests
        dem = np.load(dem_path).astype(float)
        res = 30.0 # assume 30m resolution for synthetic
    else:
        import rasterio
        with rasterio.open(dem_path) as src:
            dem = src.read(1).astype(float)
            nodata = src.nodata
            if nodata is not None:
                dem[dem == nodata] = np.nan
            res = src.transform[0]
            
    slope = calculate_slope(dem, res)
    tri = calculate_tri(dem)
    
    signature = {
        "slope_mean": np.nanmean(slope),
        "slope_std": np.nanstd(slope),
        "tri_mean": np.nanmean(tri),
        "tri_std": np.nanstd(tri)
    }
    return signature

if __name__ == "__main__":
    print("Terrain metrics module loaded.")
