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
SITE_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sites.json")


def load_earth_site_catalog(catalog_path=None):
    if catalog_path is None:
        catalog_path = SITE_CATALOG_PATH
    with open(catalog_path, encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    sites = catalog.get("sites") if isinstance(catalog, dict) else None
    if not isinstance(sites, list) or not sites:
        raise ValueError("Earth site catalog must include a non-empty sites list.")

    sites_by_id = {}
    metadata = {}
    required_fields = (
        "site_id", "name", "country", "lat", "lon", "window_km",
        "flags", "analog_for", "short_description", "verify_coordinates_manually",
    )
    required_flags = ("hyper_arid", "basaltic", "lava_tubes")
    for site in sites:
        if not isinstance(site, dict) or any(
            field not in site or site[field] is None or site[field] == ""
            for field in required_fields
        ):
            raise ValueError("Each Earth site must include all required catalog fields.")

        site_id = site["site_id"]
        if (
            not isinstance(site_id, str)
            or not site_id
            or not site_id[0].islower()
            or not site_id.replace("_", "").isalnum()
            or site_id in sites_by_id
        ):
            raise ValueError(f"Invalid or duplicate Earth site_id: {site_id!r}")

        for coordinate, lower, upper in (("lat", -90, 90), ("lon", -180, 180)):
            value = site[coordinate]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
                raise ValueError(f"Earth site '{site_id}' has an invalid {coordinate}.")

        window_km = site["window_km"]
        if isinstance(window_km, bool) or not isinstance(window_km, (int, float)) or not math.isfinite(window_km) or window_km <= 0:
            raise ValueError(f"Earth site '{site_id}' has an invalid window_km.")

        flags = site["flags"]
        if not isinstance(flags, dict) or any(
            not isinstance(flags.get(flag), bool) for flag in required_flags
        ):
            raise ValueError(f"Earth site '{site_id}' must have Boolean hyper_arid, basaltic, and lava_tubes flags.")

        analog_for = site["analog_for"]
        if not isinstance(analog_for, list) or not analog_for or any(body not in ("moon", "mars") for body in analog_for):
            raise ValueError(f"Earth site '{site_id}' analog_for must contain moon and/or mars.")
        if not isinstance(site["verify_coordinates_manually"], bool):
            raise ValueError(f"Earth site '{site_id}' must state whether coordinates need manual verification.")

        if not isinstance(site["name"], str) or not site["name"].strip() or not isinstance(site["country"], str) or not site["country"].strip() or not isinstance(site["short_description"], str) or not site["short_description"].strip():
            raise ValueError(f"Earth site '{site_id}' has invalid descriptive fields.")

        sites_by_id[site_id] = site
        type_flags = [
            label for key, label in (
                ("hyper_arid", "Hyper-arid"),
                ("basaltic", "Basaltic"),
                ("lava_tubes", "Lava tubes"),
            ) if flags[key]
        ]
        metadata[f"earth_{site_id}"] = {
            "name": site["name"],
            "country": site["country"],
            "lat": float(site["lat"]),
            "lon": float(site["lon"]),
            "type": " / ".join(type_flags) or "Terrestrial analog terrain",
            "primary_analog_for": " & ".join(body.title() for body in analog_for),
            "is_hyper_arid": flags["hyper_arid"],
            "is_basaltic": flags["basaltic"],
            "has_lava_tubes": flags["lava_tubes"],
            "description": site["short_description"],
            "analog_for": analog_for,
            "window_km": float(window_km),
            "verify_coordinates_manually": site["verify_coordinates_manually"],
        }
    return sites, metadata


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
    print("NASA SPACE APPS CHALLENGE 2026: PLANETARY ANALOG FINDER")
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
        site_records, metadata = load_earth_site_catalog()
        existing_candidate_files = [f"earth_{site['site_id']}.npy" for site in site_records]
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
    print(f"    - Mean Slope:         {target_sig['slope_mean']:.2f} deg (+/- {target_sig['slope_std']:.2f} deg)")
    print(f"    - Ruggedness (TRI):   {target_sig['tri_mean']:.2f}")
    print(f"    - Elevation Range:    {target_sig['elevation_min']:.1f}m to {target_sig['elevation_max']:.1f}m")

    # 3. Analyze Earth Candidates
    print("\n[Step 3/4] Evaluating candidate terrestrial environments...")
    if use_existing_data:
        candidate_files = existing_candidate_files
    else:
        candidate_files = [f for f in os.listdir(data_dir) if f.startswith("earth_") and f.endswith(".npy")]
    
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
    print(f"\nTOP CANDIDATE IDENTIFIED: {top_name}")
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
        print("    - target_terrain_suite.png")
        print("    - top_analog_terrain_suite.png")
        print("    - analog_compatibility_leaderboard.png")
        print("    - analog_radar_comparison.png")

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
        
    print("\nOK: Pipeline complete. Open 'dashboard/index.html' to interact with the visual web map.")
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
