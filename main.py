#!/usr/bin/env python3
"""
NASA Space Apps Challenge 2026
Planetary Terrestrial Analog Identification & Characterization Engine

Entry point CLI for running quantitative terrain signatures matching.
"""

import os
import sys
import argparse

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.terrain_metrics import extract_terrain_signature
from src.similarity_matcher import rank_candidates
from src.synthetic_generator import generate_all_datasets
from src.visualizer import plot_dem_suite, plot_analog_leaderboard, plot_radar_comparison, export_json_summary

def run_pipeline(target_key="moon", generate=True, visualize=True, output_dir="results"):
    print("=" * 70)
    print("🚀 NASA SPACE APPS CHALLENGE 2026: PLANETARY ANALOG FINDER")
    print("   Identifying Terrestrial Analogs for Moon and Mars Base Locations")
    print("=" * 70)
    
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Dataset Generation / Check
    if generate or not os.listdir(data_dir):
        print("\n[Step 1/4] Generating high-fidelity procedural planetary & terrestrial DEMs...")
        created, metadata = generate_all_datasets(data_dir=data_dir)
        print(f" -> Generated {len(created)} DEM matrices in '{data_dir}/'")
    else:
        print("\n[Step 1/4] Using existing datasets in 'data/'...")
        _, metadata = generate_all_datasets(data_dir=data_dir)

    # 2. Select Target Extraterrestrial Site
    if target_key.lower() == "mars":
        target_file = os.path.join(data_dir, "target_mars_jezero_crater.npy")
        target_display_name = "Mars (Jezero Crater - Delta & Rim)"
    else:
        target_file = os.path.join(data_dir, "target_moon_artemis_south_pole.npy")
        target_display_name = "Moon (Artemis III Lunar South Pole)"
        
    print(f"\n[Step 2/4] Extracting quantitative topographical signature for target:")
    print(f" -> Target: {target_display_name}")
    print(f" -> Source: {target_file}")
    
    target_sig, target_dem, target_slope, target_tri = extract_terrain_signature(target_file)
    print(f"    • Mean Slope:         {target_sig['slope_mean']:.2f}° (± {target_sig['slope_std']:.2f}°)")
    print(f"    • Ruggedness (TRI):   {target_sig['tri_mean']:.2f}")
    print(f"    • Elevation Range:    {target_sig['elevation_min']:.1f}m to {target_sig['elevation_max']:.1f}m")

    # 3. Analyze Earth Candidates
    print("\n[Step 3/4] Evaluating candidate terrestrial environments...")
    candidate_files = [f for f in os.listdir(data_dir) if f.startswith("earth_") and f.endswith((".npy", ".tif"))]
    
    candidates_dict = {}
    candidate_caches = {}
    
    for cfile in candidate_files:
        cpath = os.path.join(data_dir, cfile)
        cname = os.path.splitext(cfile)[0]
        sig, dem, slope, tri = extract_terrain_signature(cpath)
        candidates_dict[cname] = sig
        candidate_caches[cname] = (dem, slope, tri)
        
    # Rank candidates
    rankings = rank_candidates(target_sig, candidates_dict, metadata=metadata)
    
    print("\n" + "-" * 75)
    print(f"{'RANK':<5} | {'ANALOG SITE':<30} | {'ACI SCORE':<10} | {'PRIMARY ANALOG TYPE'}")
    print("-" * 75)
    for idx, r in enumerate(rankings, 1):
        site_meta = r["metadata"]
        display_name = site_meta.get("name", r["site_name"].replace("earth_", "").title())
        site_type = site_meta.get("type", "General Terrestrial")
        print(f"#{idx:<4} | {display_name[:30]:<30} | {r['aci']:>6.1f}%    | {site_type}")
    print("-" * 75)
    
    top_candidate = rankings[0]
    top_name = top_candidate["metadata"].get("name", top_candidate["site_name"])
    print(f"\n🏆 TOP CANDIDATE IDENTIFIED: {top_name}")
    print(f"   Analog Compatibility Index: {top_candidate['aci']}%")
    print(f"   Sub-scores:")
    for metric, score in top_candidate["sub_scores"].items():
        print(f"     - {metric:<15}: {score:.1f}% congruence")

    # 4. Generate Visualizations & Exports
    if visualize:
        print("\n[Step 4/4] Generating high-resolution analysis graphics & summary...")
        
        # Plot Target DEM suite
        plot_dem_suite(
            target_dem, target_slope, target_tri, 
            title=f"Planetary Target: {target_display_name}",
            save_path=os.path.join(output_dir, "target_terrain_suite.png")
        )
        
        # Plot Top Candidate DEM suite
        top_dem, top_slope, top_tri = candidate_caches[top_candidate["site_name"]]
        plot_dem_suite(
            top_dem, top_slope, top_tri,
            title=f"Top Earth Analog: {top_name}",
            save_path=os.path.join(output_dir, "top_analog_terrain_suite.png")
        )
        
        # Plot Leaderboard
        plot_analog_leaderboard(
            rankings, 
            target_name=target_display_name,
            save_path=os.path.join(output_dir, "analog_compatibility_leaderboard.png")
        )
        
        # Plot Radar Comparison
        plot_radar_comparison(
            target_sig, 
            candidates_dict[top_candidate["site_name"]],
            candidate_name=top_name,
            target_name=target_display_name,
            save_path=os.path.join(output_dir, "analog_radar_comparison.png")
        )
        
        # Export JSON summary
        json_file = export_json_summary(rankings, target_display_name, os.path.join(output_dir, "summary.json"))
        print(f" -> Exported quantitative summary to '{json_file}'")
        print(f" -> High-res plots saved in '{output_dir}/':")
        print("    • target_terrain_suite.png")
        print("    • top_analog_terrain_suite.png")
        print("    • analog_compatibility_leaderboard.png")
        print("    • analog_radar_comparison.png")
        
    print("\n✅ Pipeline complete! Open 'dashboard/index.html' to interact with the visual web map.")
    return rankings

def main():
    parser = argparse.ArgumentParser(description="NASA Space Apps 2026: Planetary Terrestrial Analog Finder")
    parser.add_argument("--target", choices=["moon", "mars"], default="moon", 
                        help="Target extraterrestrial destination (default: moon)")
    parser.add_argument("--generate", action="store_true", default=True, 
                        help="Procedurally generate/refresh simulation DEMs")
    parser.add_argument("--no-vis", action="store_true", 
                        help="Disable figure generation")
    parser.add_argument("--output", default="results", 
                        help="Output directory for generated reports and plots")
    args = parser.parse_args()
    
    run_pipeline(target_key=args.target, generate=args.generate, visualize=not args.no_vis, output_dir=args.output)

if __name__ == "__main__":
    main()
