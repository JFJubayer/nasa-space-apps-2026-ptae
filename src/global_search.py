#!/usr/bin/env python3
"""PTAE global analog search on real open data.

Fetches elevation (Earth: AWS Terrain Tiles, Moon: LOLA, Mars: MOLA) and NASA POWER climate, scans every
candidate region with sliding 40 km windows, and scores each against every Moon and Mars target on three
dimensions: terrain (measured), environment (measured) and geology (curated). Writes a JSON file for the
dashboard plus a CSV ranking.

Usage:  python -m src.global_search [--refresh] [--out dashboard/global_results.json]
"""

import argparse
import csv
import json
import os
import sys
from statistics import median

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import geodata
from src.analog_score import (
    DEFAULT_DIMENSION_WEIGHTS,
    ENVIRONMENT_FEATURES,
    TERRAIN_SIGMA_HETEROGENEITY,
    TERRAIN_SIGMA_MEDIAN,
    auc_separation,
    clipped_environment_target,
    composite_aci,
    describe_gaps,
    environment_similarity,
    geology_similarity,
    robust_rank_statistics,
    terrain_similarity,
)
from src.multiscale import (
    BASELINES_M,
    mask_water,
    offset_to_latlon,
    sliding_windows,
    terrain_signature,
    window_center_offset_m,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPACING_M = 120.0
WINDOW_KM = 40.0
REGION_KM = 80.0
STRIDE_KM = 10.0
MAX_WATER_FRACTION = 0.40
MARS_MIN_BASELINE_M = 960  # gridded MOLA resolves roughly 1 km features reliably
SIGMA_SCALES = (0.5, 1.0, 2.0)

REFERENCES = [
    "Kreslavsky and Head (2000) J. Geophys. Res. 105, E11: Kilometer-scale roughness of Mars from MOLA.",
    "Rosenburg et al. (2011) J. Geophys. Res. 116, E02001: Global surface slopes and roughness of the Moon from LOLA.",
    "Shepard et al. (2001) J. Geophys. Res. 106: The roughness of natural terrain.",
    "Navarro-Gonzalez et al. (2003) Science 302: Mars-like soils in the Atacama Desert.",
    "Marchant and Head (2007) Icarus 192: Antarctic dry valleys microclimate zonation and implications for Mars.",
    "McKay et al. (1994) JSC-1: A new lunar soil simulant; Allen et al. (1998) JSC Mars-1 Martian regolith simulant.",
    "Sauro et al. (2020) Earth-Science Reviews 209: Lava tubes on Earth, Moon and Mars.",
    "Hassler et al. (2014) Science 343: Mars surface radiation environment measured with MSL RAD.",
    "Zhang et al. (2020) Science Advances 6: Radiation dose on the lunar surface measured by Chang'E-4.",
    "Paige et al. (2010) Science 330: Diviner Lunar Radiometer observations of cold traps in the Moon's south polar region.",
]


def _load_json(name):
    with open(os.path.join(ROOT, "catalog", name), encoding="utf-8") as handle:
        return json.load(handle)


def _cached_array(path, builder, refresh):
    if not refresh and os.path.isfile(path):
        return np.load(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    array = builder()
    np.save(path, array)
    return array


def _norm_lon(lon):
    return ((lon + 180.0) % 360.0) - 180.0


def build_site_data(site, cache_dir, refresh):
    region = _cached_array(
        os.path.join(cache_dir, "dem", f"earth_{site['id']}_{int(REGION_KM)}km.npy"),
        lambda: geodata.fetch_earth_dem(site["lat"], site["lon"], REGION_KM, SPACING_M, cache_dir),
        refresh,
    )
    window_px = int(round(WINDOW_KM * 1000 / SPACING_M))
    stride_px = int(round(STRIDE_KM * 1000 / SPACING_M))
    windows, excluded = [], 0
    for row, col, window in sliding_windows(region, window_px, stride_px):
        if site.get("allow_below_sea_level"):
            land = window
        else:
            land, water = mask_water(window)
            if water > site.get("max_water_fraction", MAX_WATER_FRACTION):
                excluded += 1
                continue
        east, north = window_center_offset_m(region.shape, row, col, window_px, SPACING_M)
        lat, lon = offset_to_latlon(site["lat"], site["lon"], east, north)
        windows.append({"lat": lat, "lon": lon, "signature": terrain_signature(land, SPACING_M)})
    if not windows:
        raise RuntimeError(f"All windows for {site['id']} were excluded as water")
    climate = geodata.fetch_climate(site["lat"], site["lon"], cache_dir)
    return {"site": site, "windows": windows, "excluded_windows": excluded, "climate": climate}


def build_target_data(target, cache_dir, refresh):
    fetcher = geodata.fetch_moon_dem if target["body"] == "moon" else geodata.fetch_mars_dem
    lon = _norm_lon(target["lon"]) if target["body"] == "mars" else target["lon"]
    dem = _cached_array(
        os.path.join(cache_dir, "dem", f"{target['body']}_{target['id']}_{int(WINDOW_KM)}km.npy"),
        lambda: fetcher(target["lat"], lon, WINDOW_KM, SPACING_M),
        refresh,
    )
    signature = terrain_signature(dem, SPACING_M)
    valid = [b for b in signature["baselines_m"] if target["body"] == "moon" or b >= MARS_MIN_BASELINE_M]
    return {"target": target, "signature": signature, "valid_baselines": valid}


def score_target(target_data, site_data, earth_floor, env_sigma):
    target = target_data["target"]
    env_target = clipped_environment_target(earth_floor)
    results = {}
    for site_id, data in site_data.items():
        site = data["site"]
        sims = {
            scale: np.array([
                terrain_similarity(target_data["signature"], w["signature"], target_data["valid_baselines"], scale)
                for w in data["windows"]
            ])
            for scale in SIGMA_SCALES
        }
        best_index = int(np.argmax(sims[1.0]))
        best_window = data["windows"][best_index]
        environment, env_features = environment_similarity(data["climate"], env_target, env_sigma)
        env_by_scale = [environment_similarity(data["climate"], env_target, env_sigma, scale)[0] for scale in SIGMA_SCALES]
        geology = geology_similarity(site["tags"], target["tags"])
        valid = target_data["valid_baselines"]
        results[site_id] = {
            "terrain": float(sims[1.0][best_index]),
            "terrain_typical": float(np.median(sims[1.0])),
            "coverage": float(np.mean(sims[1.0] >= 0.5)),
            "terrain_by_scale": [float(sims[s].max()) for s in SIGMA_SCALES],
            "environment": environment,
            "environment_by_scale": env_by_scale,
            "env_features": env_features,
            "geology": geology,
            "best_window": best_window,
            "n_windows": len(data["windows"]),
            "gaps": describe_gaps(target_data["signature"], best_window["signature"], data["climate"], env_target, valid, env_sigma),
        }
    return results


def _pct(value):
    return round(100.0 * float(value), 1)


def run(out_path, csv_path, cache_dir, refresh=False):
    sites_catalog = _load_json("earth_sites.json")
    targets_catalog = _load_json("targets.json")
    earth_floor = targets_catalog["earth_floor"]
    env_sigma = targets_catalog["environment_sigma"]

    print(f"Fetching and analysing {len(sites_catalog['sites'])} Earth regions...")
    site_data = {}
    for site in sites_catalog["sites"]:
        print(f"  - {site['name']}")
        site_data[site["id"]] = build_site_data(site, cache_dir, refresh)

    print(f"Fetching {len(targets_catalog['targets'])} Moon/Mars targets...")
    target_data = {}
    for target in targets_catalog["targets"]:
        print(f"  - {target['name']}")
        target_data[target["id"]] = build_target_data(target, cache_dir, refresh)

    weights = DEFAULT_DIMENSION_WEIGHTS
    target_outputs = []
    aci_by_target = {}
    validation_rows = []
    for target_id, tdata in target_data.items():
        scored = score_target(tdata, site_data, earth_floor, env_sigma)
        robust = robust_rank_statistics({
            sid: {
                "terrain_by_scale": r["terrain_by_scale"],
                "environment": r["environment"],
                "geology": r["geology"],
            }
            for sid, r in scored.items()
        })
        rows = []
        for site_id, r in scored.items():
            site = site_data[site_id]["site"]
            aci = composite_aci(r["terrain"], r["environment"], r["geology"], weights)
            aci_additive = composite_aci(r["terrain"], r["environment"], r["geology"], weights, "additive")
            profile = r["best_window"]["signature"]
            rows.append({
                "site_id": site_id,
                "aci": round(aci, 2),
                "aci_additive": round(aci_additive, 2),
                "terrain": _pct(r["terrain"]),
                "environment": _pct(r["environment"]),
                "geology": _pct(r["geology"]),
                "terrain_typical": _pct(r["terrain_typical"]),
                "coverage": _pct(r["coverage"]),
                "n_windows": r["n_windows"],
                "best_window": {"lat": round(r["best_window"]["lat"], 4), "lon": round(r["best_window"]["lon"], 4)},
                "slope_profile": {
                    "baselines_m": profile["baselines_m"],
                    "median_deg": [round(v, 3) for v in profile["median_slope_deg"]],
                    "p90_deg": [round(v, 3) for v in profile["p90_slope_deg"]],
                    "hurst": round(profile["hurst"], 3),
                    "relief_m": round(profile["relief_m"], 1),
                },
                "env_features": {k: _pct(v) for k, v in r["env_features"].items()},
                "gaps": r["gaps"],
                "robust": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in robust[site_id].items()},
                "category": site["category"],
            })
        rows.sort(key=lambda row: row["aci"], reverse=True)
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
        aci_by_target[target_id] = {row["site_id"]: row for row in rows}

        positives = [row for row in rows if row["category"] != "control"]
        negatives = [row for row in rows if row["category"] == "control"]
        validation_rows.append({
            "target_id": target_id,
            "auc_aci": auc_separation([p["aci"] for p in positives], [n["aci"] for n in negatives]),
            "auc_aci_additive": auc_separation([p["aci_additive"] for p in positives], [n["aci_additive"] for n in negatives]),
            "auc_terrain": auc_separation([p["terrain"] for p in positives], [n["terrain"] for n in negatives]),
            "auc_environment": auc_separation([p["environment"] for p in positives], [n["environment"] for n in negatives]),
            "auc_geology": auc_separation([p["geology"] for p in positives], [n["geology"] for n in negatives]),
            "best_control_rank": min(row["rank"] for row in negatives),
            "terrain_vs_full_spearman": float(spearmanr(
                [row["terrain"] for row in rows], [row["aci"] for row in rows]
            ).statistic),
        })
        tgt = tdata["target"]
        target_outputs.append({
            "id": tgt["id"], "name": tgt["name"], "body": tgt["body"], "lat": tgt["lat"], "lon": _norm_lon(tgt["lon"]),
            "why": tgt["why"], "dem": tgt["dem"], "tags": tgt["tags"],
            "valid_baselines_m": tdata["valid_baselines"],
            "slope_profile": {
                "baselines_m": tdata["signature"]["baselines_m"],
                "median_deg": [round(v, 3) for v in tdata["signature"]["median_slope_deg"]],
                "p90_deg": [round(v, 3) for v in tdata["signature"]["p90_slope_deg"]],
                "hurst": round(tdata["signature"]["hurst"], 3),
                "relief_m": round(tdata["signature"]["relief_m"], 1),
            },
            "rankings": rows,
        })

    body_summary = {}
    for body in ("moon", "mars"):
        ids = [t["id"] for t in target_outputs if t["body"] == body]
        per_site = []
        for site in sites_catalog["sites"]:
            acis = [aci_by_target[t][site["id"]]["aci"] for t in ids]
            ranks = [aci_by_target[t][site["id"]]["rank"] for t in ids]
            per_site.append({"site_id": site["id"], "mean_aci": round(float(np.mean(acis)), 2),
                             "min_aci": round(float(np.min(acis)), 2), "max_aci": round(float(np.max(acis)), 2),
                             "median_rank": float(median(ranks)), "category": site["category"]})
        per_site.sort(key=lambda row: row["mean_aci"], reverse=True)
        for rank, row in enumerate(per_site, 1):
            row["rank"] = rank
        body_summary[body] = {"targets": ids, "rankings": per_site}

    payload = {
        "schema_version": 2,
        "method": {
            "grid_spacing_m": SPACING_M, "window_km": WINDOW_KM, "region_km": REGION_KM, "stride_km": STRIDE_KM,
            "baselines_m": list(BASELINES_M), "mars_min_valid_baseline_m": MARS_MIN_BASELINE_M,
            "dimension_weights": weights,
            "aggregation": "weighted geometric mean (non-compensatory); additive mean reported as aci_additive",
            "terrain_sigma_ln": {"median_slope": TERRAIN_SIGMA_MEDIAN, "heterogeneity": TERRAIN_SIGMA_HETEROGENEITY},
            "environment_features": list(ENVIRONMENT_FEATURES),
            "earth_floor": earth_floor, "environment_sigma": env_sigma,
            "robustness": "1000 random draws: Dirichlet dimension weights around the defaults and terrain tolerance scales of 0.5x, 1x or 2x.",
            "data": {
                "earth_elevation": "AWS Terrain Tiles zoom 11 (SRTM/NASADEM/ArcticDEM composite), resampled to 120 m",
                "moon_elevation": "LRO LOLA 20 m south-polar DEM, block-averaged to 120 m",
                "mars_elevation": "MGS MOLA 463 m global DEM, bilinearly resampled to 120 m (baselines >= 960 m only)",
                "climate": "NASA POWER climatology (0.5 deg reanalysis; coarse for point sites)",
                "geology": "Curated expert priors in catalog/earth_sites.json and catalog/targets.json",
            },
        },
        "tag_vocabulary": sites_catalog["tag_vocabulary"],
        "irreducible_gaps": targets_catalog["irreducible_gaps"],
        "references": REFERENCES,
        "validation": {
            "per_target": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()} for row in validation_rows],
            "mean_auc_aci": round(float(np.nanmean([r["auc_aci"] for r in validation_rows])), 3),
            "mean_auc_aci_additive": round(float(np.nanmean([r["auc_aci_additive"] for r in validation_rows])), 3),
            "mean_auc_terrain": round(float(np.nanmean([r["auc_terrain"] for r in validation_rows])), 3),
            "mean_auc_environment": round(float(np.nanmean([r["auc_environment"] for r in validation_rows])), 3),
            "mean_auc_geology": round(float(np.nanmean([r["auc_geology"] for r in validation_rows])), 3),
            "control_sites": [s["id"] for s in sites_catalog["sites"] if s["category"] == "control"],
        },
        "sites": [
            {
                **{k: s[k] for k in ("id", "name", "country", "lat", "lon", "category", "tags", "heritage", "limits")},
                "climate": site_data[s["id"]]["climate"],
                "n_windows": len(site_data[s["id"]]["windows"]),
                "excluded_water_windows": site_data[s["id"]]["excluded_windows"],
            }
            for s in sites_catalog["sites"]
        ],
        "targets": target_outputs,
        "body_summary": body_summary,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
    print(f"Wrote {out_path}")

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["target", "rank", "site", "category", "aci", "terrain", "environment", "geology",
                         "best_window_lat", "best_window_lon", "prob_top3"])
        names = {s["id"]: s["name"] for s in sites_catalog["sites"]}
        for tgt in target_outputs:
            for row in tgt["rankings"]:
                writer.writerow([tgt["id"], row["rank"], names[row["site_id"]], row["category"], row["aci"],
                                 row["terrain"], row["environment"], row["geology"],
                                 row["best_window"]["lat"], row["best_window"]["lon"], row["robust"]["prob_top3"]])
    print(f"Wrote {csv_path}")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=os.path.join(ROOT, "dashboard", "global_results.json"))
    parser.add_argument("--csv", default=os.path.join(ROOT, "results", "global_ranking.csv"))
    parser.add_argument("--cache", default=os.path.join(ROOT, "cache"))
    parser.add_argument("--refresh", action="store_true", help="Re-download elevation windows instead of using the cache")
    args = parser.parse_args(argv)
    run(args.out, args.csv, args.cache, args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
