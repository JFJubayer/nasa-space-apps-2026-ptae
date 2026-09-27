import os
import numpy as np

def create_crater(dem, center_x, center_y, radius, depth):
    """Adds a bowl-shaped crater to the DEM."""
    y, x = np.ogrid[:dem.shape[0], :dem.shape[1]]
    dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    
    # Crater interior (bowl)
    mask = dist_from_center <= radius
    dem[mask] -= depth * (1 - (dist_from_center[mask] / radius)**2)
    
    # Crater rim (raised edges)
    rim_mask = (dist_from_center > radius) & (dist_from_center <= radius * 1.2)
    dem[rim_mask] += (depth * 0.2) * (1 - (dist_from_center[rim_mask] - radius) / (radius * 0.2))
    return dem

def generate_moon():
    # Base terrain: high elevation, very rough
    dem = np.random.normal(loc=1000, scale=15, size=(500, 500))
    # Add many craters
    for _ in range(50):
        cx, cy = np.random.randint(0, 500, 2)
        r = np.random.randint(10, 50)
        d = np.random.randint(20, 100)
        dem = create_crater(dem, cx, cy, r, d)
    return dem

def generate_atacama():
    # Base terrain: High plateau, fairly smooth but rolling hills
    dem = np.random.normal(loc=2500, scale=2, size=(500, 500))
    # Add a gentle slope
    x = np.linspace(0, 100, 500)
    dem += np.tile(x, (500, 1))
    return dem

def generate_iceland():
    # Base terrain: Rugged, volcanic, very rough like the moon but less deep craters
    dem = np.random.normal(loc=500, scale=15, size=(500, 500))
    # Add volcanic calderas (look like craters)
    for _ in range(30):
        cx, cy = np.random.randint(0, 500, 2)
        r = np.random.randint(10, 40)
        d = np.random.randint(20, 80)
        dem = create_crater(dem, cx, cy, r, d)
    return dem

def generate_death_valley():
    # Base terrain: Flat basin
    dem = np.random.normal(loc=-50, scale=1, size=(500, 500))
    # Steep mountain edges on the sides
    dem[:, :50] += np.linspace(500, 0, 50)
    dem[:, -50:] += np.linspace(0, 500, 50)
    return dem

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    
    print("Generating synthetic DEMs...")
    np.save("data/moon_artemis_south_pole.npy", generate_moon())
    print(" - Created Moon (Artemis South Pole)")
    
    np.save("data/earth_atacama.npy", generate_atacama())
    print(" - Created Earth (Atacama)")
    
    np.save("data/earth_iceland.npy", generate_iceland())
    print(" - Created Earth (Iceland)")
    
    np.save("data/earth_death_valley.npy", generate_death_valley())
    print(" - Created Earth (Death Valley)")
    
    print("\nDone! Run find_analog.py to compare them.")
