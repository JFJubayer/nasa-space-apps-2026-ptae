#!/usr/bin/env python3
"""
NASA Space Apps Challenge 2026
Planetary Terrestrial Analog Identification & Characterization Engine

Entry point CLI for running quantitative terrain signatures matching.
"""

import os
import sys
import argparse
import json
import math

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.terrain_metrics import extract_terrain_signature
from src.similarity_matcher import rank_candidates
from src.synthetic_generator import generate_all_datasets
from src.visualizer import plot_dem_suite, plot_analog_leaderboard, plot_radar_comparison, export_json_summary

ACI_METRICS = ("slope_mean", "slope_std", "tri_mean", "tri_std", "elevation_std")


def load_target_site_catalog(catalog_path=None):
    if catalog_path is None:
        catalog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "target_sites.json")
    with open(catalog_path, encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    sites = catalog.get("target_sites")
    if not isinstance(sites, list) or not sites:
        raise ValueError("Target-site catalog must include a non-empty target_sites list.")
    sites_by_id = {}
    required_fields = ("id", "name", "body", "lat", "lon", "short_description", "key_features", "mission_relevance", "source_note")
    for site in sites:
        if not isinstance(site, dict) or any(field not in site or site[field] is None or site[field] == "" for field in required_fields):
            raise ValueError("Each target site must include its required descriptive fields.")
        if site["body"] not in ("Moon", "Mars") or site.get("coords_approximate") is not True:
            raise ValueError(f"Target site '{site['id']}' must identify its body and mark coordinates approximate.")
        if site["id"] in sites_by_id:
            raise ValueError(f"Duplicate target-site id: {site['id']}")
        sites_by_id[site["id"]] = site

    analog_matches = catalog.get("analog_matches")
    if not isinstance(analog_matches, dict):
        raise ValueError("Target-site catalog must include analog_matches by body.")
    for body in ("moon", "mars"):
        matches = analog_matches.get(body)
        if not isinstance(matches, list) or not matches:
            raise ValueError(f"Target-site catalog must include qualitative {body} matches.")
        for match in matches:
            site = sites_by_id.get(match.get("target_site_id"))
            if not site or site["body"].lower() != body:
                raise ValueError(f"Invalid {body} target-site match: {match.get('target_site_id')}")
            if not set(match.get("shared_features", [])).issubset(site["key_features"]):
                raise ValueError(f"Match features must come from target key_features for {site['id']}.")
    return catalog


def export_ranked_results(target_key, target_name, target_sig, rankings, candidates, output_path, target_catalog=None):
    target_catalog = target_catalog or load_target_site_catalog()
    target_body = target_key.lower()
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    records = []
    for rank, result in enumerate(rankings, 1):
        site_id = result["site_name"]
        site_metadata = result["metadata"]
        records.append({
            "rank": rank,
            "site_name": site_metadata.get("name", site_id),
            "site_id": site_id,
            "base_topographic_score": result["base_topographic_score"],
            "applied_bonus": result["applied_bonus"],
            "aci": result["aci"],
            "capped": result["capped"],
            "terrain_metrics": {metric: candidates[site_id][metric] for metric in ACI_METRICS},
            "sub_scores": result["sub_scores"],
            "metadata": site_metadata,
        })

    payload = {
        "target": target_body,
        "target_name": target_name,
        "target_terrain_metrics": {metric: target_sig[metric] for metric in ACI_METRICS},
        "target_sites": [site for site in target_catalog["target_sites"] if site["body"].lower() == target_body],
        "analog_matches": target_catalog["analog_matches"][target_body],
        "analog_match_basis": target_catalog.get("match_basis", "Qualitative shared-feature mapping; not ACI."),
        "rankings": records,
    }
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2)
    return output_path


def _resolution_for_dem(dem_path, use_existing_data):
    default_resolution = 30.0
    if not use_existing_data:
        return default_resolution

    sidecar_path = os.path.splitext(dem_path)[0] + ".json"
    if not os.path.isfile(sidecar_path):
        print(f"WARNING: No resolution sidecar for '{os.path.basename(dem_path)}'; using {default_resolution} m/pixel.")
        return default_resolution

    with open(sidecar_path, encoding="utf-8") as sidecar:
        metadata = json.load(sidecar)
    resolution = metadata.get("output_ground_resolution_m_per_pixel")
    if isinstance(resolution, bool) or not isinstance(resolution, (int, float)) or not math.isfinite(resolution) or resolution <= 0:
        print(f"WARNING: Sidecar '{os.path.basename(sidecar_path)}' has no valid output ground resolution; using {default_resolution} m/pixel.")
        return default_resolution
    return float(resolution)


def run_pipeline(target_key="moon", generate=True, visualize=True, output_dir="results", json_output_path=None, use_existing_data=False, data_dir="data"):
    print("=" * 70)
    print("🚀 NASA SPACE APPS CHALLENGE 2026: PLANETARY ANALOG FINDER")
    print("   Identifying Terrestrial Analogs for Moon and Mars Base Locations")
    print("=" * 70)
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    if target_key.lower() == "mars":
        target_filename = "target_mars_jezero_crater.npy"
        target_display_name = "Mars (Jezero Crater - Delta & Rim)"
    else:
        target_filename = "target_moon_artemis_south_pole.npy"
        target_display_name = "Moon (Artemis III Lunar South Pole)"
    target_file = os.path.join(data_dir, target_filename)
    
    # 1. Dataset Generation / Check
    existing_candidate_files = None
    if use_existing_data:
        dataset_paths, metadata = generate_all_datasets(data_dir=data_dir, generate=False)
        existing_candidate_files = [
            os.path.basename(path)
            for path in dataset_paths
            if os.path.basename(path).startswith("earth_")
        ]
        required_files = [target_file] + [
            os.path.join(data_dir, filename) for filename in existing_candidate_files
        ]
        missing_files = [path for path in required_files if not os.path.isfile(path)]
        if missing_files:
            missing_names = ", ".join(os.path.basename(path) for path in missing_files)
            raise FileNotFoundError(f"Missing required DEM file(s) in '{data_dir}/': {missing_names}")
        print("\n[Step 1/4] Using existing planetary and terrestrial DEMs in 'data/'...")
    elif generate or not os.listdir(data_dir):
        print("\n[Step 1/4] Generating high-fidelity procedural planetary & terrestrial DEMs...")
        created, metadata = generate_all_datasets(data_dir=data_dir)
        print(f" -> Generated {len(created)} DEM matrices in '{data_dir}/'")
    else:
        print("\n[Step 1/4] Using existing datasets in 'data/'...")
        _, metadata = generate_all_datasets(data_dir=data_dir)

    # 2. Select Target Extraterrestrial Site
    print(f"\n[Step 2/4] Extracting quantitative topographical signature for target:")
    print(f" -> Target: {target_display_name}")
    print(f" -> Source: {target_file}")
    
    target_resolution = _resolution_for_dem(target_file, use_existing_data)
    target_sig, target_dem, target_slope, target_tri = extract_terrain_signature(
        target_file, resolution=target_resolution
    )
    print(f"    • Mean Slope:         {target_sig['slope_mean']:.2f}° (± {target_sig['slope_std']:.2f}°)")
    print(f"    • Ruggedness (TRI):   {target_sig['tri_mean']:.2f}")
    print(f"    • Elevation Range:    {target_sig['elevation_min']:.1f}m to {target_sig['elevation_max']:.1f}m")

    # 3. Analyze Earth Candidates
    print("\n[Step 3/4] Evaluating candidate terrestrial environments...")
    if use_existing_data:
        candidate_files = existing_candidate_files
    else:
        candidate_files = [f for f in os.listdir(data_dir) if f.startswith("earth_") and f.endswith((".npy", ".tif"))]
    
    candidates_dict = {}
    candidate_caches = {}
    
    for cfile in candidate_files:
        cpath = os.path.join(data_dir, cfile)
        cname = os.path.splitext(cfile)[0]
        resolution = _resolution_for_dem(cpath, use_existing_data)
        sig, dem, slope, tri = extract_terrain_signature(cpath, resolution=resolution)
        candidates_dict[cname] = sig
        candidate_caches[cname] = (dem, slope, tri)
        
    # Rank candidates
    rankings = rank_candidates(target_sig, candidates_dict, metadata=metadata)
    
    print("\n" + "-" * 126)
    print(f"{'RANK':<5} | {'ANALOG SITE':<34} | {'BASE':>8} | {'BONUS':>7} | {'FINAL ACI':>12} | {'PRIMARY ANALOG TYPE'}")
    print("-" * 126)
    for idx, r in enumerate(rankings, 1):
        site_meta = r["metadata"]
        display_name = site_meta.get("name", r["site_name"].replace("earth_", "").title())
        site_type = site_meta.get("type", "General Terrestrial")
        capped_marker = " *" if r["capped"] else ""
        print(f"#{idx:<4} | {display_name[:34]:<34} | {r['base_topographic_score']:>7.2f}% | +{r['applied_bonus']:>5.2f} | {r['aci']:>7.2f}%{capped_marker:<3} | {site_type}")
    print("-" * 126)
    if any(result["capped"] for result in rankings):
        print("* Final score capped below 100 for a non-perfect metric match.")
    
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

    if json_output_path:
        json_file = export_ranked_results(
            target_key,
            target_display_name,
            target_sig,
            rankings,
            candidates_dict,
            json_output_path,
        )
        print(f" -> Exported ranked candidate details to '{json_file}'")
        
    print("\n✅ Pipeline complete! Open 'dashboard/index.html' to interact with the visual web map.")
    return rankings

def main():
    parser = argparse.ArgumentParser(description="NASA Space Apps 2026: Planetary Terrestrial Analog Finder")
    parser.add_argument("--target", choices=["moon", "mars"], default="moon", 
                        help="Target extraterrestrial destination (default: moon)")
    parser.add_argument("--generate", action="store_true", default=True, 
                        help="Procedurally generate/refresh simulation DEMs")
    parser.add_argument(
        "--use-existing-data",
        action="store_true",
        help="Use required DEM files in --data-dir instead of generating synthetic DEMs",
    )
    parser.add_argument("--data-dir", default="data", help="DEM input/output directory (default: data)")
    parser.add_argument("--no-vis", action="store_true", 
                        help="Disable figure generation")
    parser.add_argument("--output", default="results", 
                        help="Output directory for generated reports and plots")
    parser.add_argument(
        "--json-out",
        nargs="?",
        const=True,
        default=None,
        metavar="PATH",
        help="Write ranked scores and terrain metrics to PATH (default: dashboard/results_<target>.json)",
    )
    args = parser.parse_args()

    json_output_path = args.json_out
    if args.json_out is True:
        json_output_path = os.path.join("dashboard", f"results_{args.target}.json")
    
    run_pipeline(
        target_key=args.target,
        generate=args.generate,
        use_existing_data=args.use_existing_data,
        data_dir=args.data_dir,
        visualize=not args.no_vis,
        output_dir=args.output,
        json_output_path=json_output_path,
    )

if __name__ == "__main__":
    main()
