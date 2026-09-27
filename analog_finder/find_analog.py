import os
import math
from compute_terrain_metrics import extract_signatures

def calculate_similarity(sig1, sig2):
    """
    Calculate a similarity score between two topographical signatures.
    Lower score means they are more similar (distance in feature space).
    """
    # Normalize weights (can be adjusted based on importance)
    w_slope = 1.0
    w_tri = 1.0
    
    diff_slope = ((sig1['slope_mean'] - sig2['slope_mean']) ** 2 + 
                  (sig1['slope_std'] - sig2['slope_std']) ** 2) * w_slope
                  
    diff_tri = ((sig1['tri_mean'] - sig2['tri_mean']) ** 2 + 
                (sig1['tri_std'] - sig2['tri_std']) ** 2) * w_tri
                
    return math.sqrt(diff_slope + diff_tri)

def main():
    print("🚀 NASA Space Apps 2026: Earth Analog Finder")
    print("--------------------------------------------")
    
    # Using synthetic .npy files for demonstration.
    # In a real scenario, replace these with .tif files downloaded from NASA Earthdata and PDS.
    lunar_target_dem = "data/moon_artemis_south_pole.npy"
    earth_candidate_dems = [
        "data/earth_atacama.npy",
        "data/earth_iceland.npy",
        "data/earth_death_valley.npy"
    ]
    
    if not os.path.exists(lunar_target_dem):
        print("⚠️ Data files not found. Please run 'python generate_synthetic_dems.py' first.")
        return

    print(f"Extracting signature for target: {lunar_target_dem}...")
    target_sig = extract_signatures(lunar_target_dem)
    
    best_match = None
    best_score = float('inf')
    
    print("\nEvaluating Earth candidates...")
    for candidate in earth_candidate_dems:
        if not os.path.exists(candidate):
            continue
            
        candidate_sig = extract_signatures(candidate)
        score = calculate_similarity(target_sig, candidate_sig)
        
        print(f" - {candidate}: Similarity Score = {score:.2f}")
        
        if score < best_score:
            best_score = score
            best_match = candidate
            
    if best_match:
        print(f"\n✅ Best Earth Analog Found: {best_match} (Score: {best_score:.2f})")
        print("   This location has the closest slope and ruggedness profile to the Lunar South Pole target!")

if __name__ == "__main__":
    main()
