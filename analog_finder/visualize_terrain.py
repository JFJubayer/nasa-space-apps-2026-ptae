import os
import numpy as np
import matplotlib.pyplot as plt
from compute_terrain_metrics import calculate_slope, calculate_tri

def plot_terrain_metrics(dem_path):
    """
    Loads a DEM (.npy or .tif) and plots its Elevation, Slope, and TRI side-by-side.
    """
    if not os.path.exists(dem_path):
        print(f"⚠️ Could not find {dem_path}. Please generate or download the data first.")
        return

    print(f"Visualizing {dem_path}...")
    
    # Load data
    if dem_path.endswith('.npy'):
        dem = np.load(dem_path).astype(float)
        res = 30.0
    else:
        import rasterio
        with rasterio.open(dem_path) as src:
            dem = src.read(1).astype(float)
            nodata = src.nodata
            if nodata is not None:
                dem[dem == nodata] = np.nan
            res = src.transform[0]
            
    # Compute metrics
    slope = calculate_slope(dem, res)
    tri = calculate_tri(dem)
    
    # Set up the plot
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f"Terrain Analysis: {os.path.basename(dem_path)}", fontsize=16)
    
    # Plot Elevation
    im0 = axes[0].imshow(dem, cmap='terrain')
    axes[0].set_title('Elevation (DEM)')
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label='Elevation')
    
    # Plot Slope
    im1 = axes[1].imshow(slope, cmap='hot')
    axes[1].set_title('Slope (Degrees)')
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label='Degrees')
    
    # Plot TRI (Ruggedness)
    im2 = axes[2].imshow(tri, cmap='magma')
    axes[2].set_title('Terrain Ruggedness Index (TRI)')
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04, label='Ruggedness')
    
    for ax in axes:
        ax.axis('off')
        
    plt.tight_layout()
    
    # Save the figure
    output_filename = os.path.basename(dem_path).replace('.npy', '.png').replace('.tif', '.png')
    output_path = os.path.join(os.path.dirname(dem_path), output_filename)
    plt.savefig(output_path, dpi=300)
    print(f"✅ Saved visualization to {output_path}")
    
    # Uncomment the line below if you want the window to pop up when running locally
    # plt.show()

if __name__ == "__main__":
    # Test visualization on the generated synthetic data
    targets = [
        "data/moon_artemis_south_pole.npy",
        "data/earth_iceland.npy",
        "data/earth_atacama.npy",
        "data/earth_death_valley.npy"
    ]
    
    for target in targets:
        plot_terrain_metrics(target)
