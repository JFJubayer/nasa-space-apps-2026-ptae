#!/usr/bin/env python3
"""Analyze ACI weight robustness without modifying source DEMs or rankings."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import _resolution_for_dem, load_earth_site_catalog
from src.similarity_matcher import DEFAULT_WEIGHTS, rank_candidates
from src.terrain_metrics import extract_terrain_signature

METRICS = tuple(DEFAULT_WEIGHTS)
RANDOM_SEED = 42
RANDOM_SCENARIO_COUNT = 1000
OUTPUT_PATH = PROJECT_ROOT / "dashboard" / "weight_sensitivity.json"
PROTECTED_HASHES = {
    "results_moon.json": "2D4E902F070B6A2AEEA23062A51FDD284FD3106FEB82F3ECB9AB853D8950845E",
    "results_mars.json": "F3E06E6777476359FC80A43024A0309A76C01E15E3DDA70FF5B48FF9223124BC",
}


def verify_protected_rankings():
    hashes = {}
    for filename, expected in PROTECTED_HASHES.items():
        actual = hashlib.sha256((PROJECT_ROOT / "dashboard" / filename).read_bytes()).hexdigest().upper()
        if actual != expected:
            raise ValueError(f"Protected ranking hash mismatch for {filename}; refusing to write analysis.")
        hashes[filename] = actual
    return hashes


def build_scenarios(seed=RANDOM_SEED, random_count=RANDOM_SCENARIO_COUNT):
    baseline = dict(DEFAULT_WEIGHTS)
    scenarios = []

    def add(scenario_id, family, weights, bonus_enabled=True):
        total = sum(weights.values())
        scenarios.append({
            "scenario_id": scenario_id,
            "family": family,
            "weights": {metric: float(weights[metric] / total) for metric in METRICS},
            "flag_bonus_enabled": bonus_enabled,
        })

    add("baseline", "baseline", baseline)
    for metric in METRICS:
        for factor in (0.5, 1.5):
            weights = dict(baseline)
            weights[metric] *= factor
            add(f"oat_{metric}_x{factor}", "one_at_a_time", weights)
    add("equal_weights", "equal_weights", dict.fromkeys(METRICS, 1.0))
    for metric in METRICS:
        weights = dict(baseline)
        weights[metric] = 0.0
        add(f"drop_{metric}", "drop_one_metric", weights)
    rng = np.random.default_rng(seed)
    for index, vector in enumerate(rng.dirichlet(np.ones(len(METRICS)), size=random_count), 1):
        add(f"random_{index:04d}", "random", dict(zip(METRICS, vector)))
    add("flag_bonus_off", "flag_bonus_off", baseline, bonus_enabled=False)
    return scenarios


def spearman_rank_correlation(baseline_order, comparison_order):
    """Use ranker-ordered positions, as in the existing window sensitivity."""
    if len(set(baseline_order)) != len(baseline_order) or set(baseline_order) != set(comparison_order):
        raise ValueError("Rank correlations require the same unique site IDs.")
    if len(baseline_order) != len(comparison_order) or len(baseline_order) < 2:
        raise ValueError("Rank correlations require equally sized rankings of at least two sites.")
    baseline_ranks = {site_id: rank for rank, site_id in enumerate(baseline_order, 1)}
    comparison_ranks = {site_id: rank for rank, site_id in enumerate(comparison_order, 1)}
    count = len(baseline_order)
    difference_sum = sum((baseline_ranks[site_id] - comparison_ranks[site_id]) ** 2 for site_id in baseline_order)
    return round(1.0 - 6.0 * difference_sum / (count * (count ** 2 - 1)), 6)


def load_signatures():
    sites, metadata = load_earth_site_catalog()
    if len(sites) != 20:
        raise ValueError(f"Expected 20 Earth candidates, found {len(sites)}.")

    def signature(filename):
        dem_path = PROJECT_ROOT / "data_real" / filename
        sidecar = json.loads(dem_path.with_suffix(".json").read_text(encoding="utf-8"))
        resolution = sidecar.get("output_ground_resolution_m_per_pixel")
        if isinstance(resolution, bool) or not isinstance(resolution, (int, float)) or not np.isfinite(resolution) or resolution <= 0:
            raise ValueError(f"Missing or invalid prepared-grid resolution for {filename}.")
        result, dem, _, _ = extract_terrain_signature(
            str(dem_path), resolution=_resolution_for_dem(str(dem_path), use_existing_data=True)
        )
        if dem.shape != (300, 300):
            raise ValueError(f"Expected an unchanged 300x300 DEM for {filename}, found {dem.shape}.")
        return result

    candidates = {
        f"earth_{site['site_id']}": signature(f"earth_{site['site_id']}.npy")
        for site in sites
    }
    targets = {
        "moon": signature("target_moon_artemis_south_pole.npy"),
        "mars": signature("target_mars_jezero_crater.npy"),
    }
    return targets, candidates, metadata


def assert_baseline_matches(body, rankings):
    reference = json.loads((PROJECT_ROOT / "dashboard" / f"results_{body}.json").read_text(encoding="utf-8"))
    expected = [(entry["site_id"], entry["aci"]) for entry in reference["rankings"]]
    actual = [(entry["site_name"], entry["aci"]) for entry in rankings]
    if actual != expected:
        raise ValueError(
            f"Baseline mismatch for {body}: order and ACI must exactly match results_{body}.json; "
            "refusing to write analysis. No inputs or scores will be changed."
        )


def summarize(results, baseline_leader):
    count = len(results)
    correlations = [result["spearman_vs_baseline"] for result in results]
    first_count = sum(result["leader_site_id"] == baseline_leader for result in results)
    top_three_count = sum(result["baseline_leader_rank"] <= 3 for result in results)
    return {
        "scenario_count": count,
        "leader_retained_count": first_count,
        "leader_stability_percent": round(100.0 * first_count / count, 6),
        "top3_retained_count": top_three_count,
        "top3_stability_percent": round(100.0 * top_three_count / count, 6),
        "min_spearman": min(correlations),
        "median_spearman": float(np.median(correlations)),
        "leader_changes": [
            {
                "scenario_id": result["scenario_id"],
                "replacement_site_id": result["leader_site_id"],
                "replacement_aci": result["leader_aci"],
            }
            for result in results if result["leader_site_id"] != baseline_leader
        ],
    }


def build_payload():
    initial_hashes = verify_protected_rankings()
    targets, candidates, metadata = load_signatures()
    scenarios = build_scenarios()
    baselines = {}
    for body, signature in targets.items():
        baseline = rank_candidates(signature, candidates, weights=scenarios[0]["weights"], metadata=metadata)
        assert_baseline_matches(body, baseline)
        baselines[body] = baseline

    target_results = {}
    for body, signature in targets.items():
        baseline_order = [entry["site_name"] for entry in baselines[body]]
        baseline_leader = baseline_order[0]
        results = []
        for scenario in scenarios:
            rankings = rank_candidates(
                signature, candidates, weights=scenario["weights"],
                metadata=metadata if scenario["flag_bonus_enabled"] else None,
            )
            order = [entry["site_name"] for entry in rankings]
            results.append({
                "scenario_id": scenario["scenario_id"],
                "leader_site_id": order[0],
                "leader_aci": rankings[0]["aci"],
                "top5_site_ids": order[:5],
                "baseline_leader_rank": order.index(baseline_leader) + 1,
                "spearman_vs_baseline": spearman_rank_correlation(baseline_order, order),
            })
        target_results[body] = {
            "baseline_leader_site_id": baseline_leader,
            "baseline_ranking": [{"site_id": entry["site_name"], "aci": entry["aci"]} for entry in baselines[body]],
            "summary": summarize(results, baseline_leader),
            "random_only_summary": summarize(
                [result for result, scenario in zip(results, scenarios) if scenario["family"] == "random"],
                baseline_leader,
            ),
            "scenarios": results,
        }

    final_hashes = verify_protected_rankings()
    if final_hashes != initial_hashes:
        raise ValueError("Protected ranking files changed during analysis; refusing to write.")
    return {
        "schema_version": 1,
        "protocol": {
            "inputs": "Full existing 300x300 arrays in data_real, catalog order and prepared-grid sidecar resolutions; no cropping or resampling.",
            "metrics": list(METRICS),
            "baseline_weights": dict(DEFAULT_WEIGHTS),
            "one_at_a_time_factors": [0.5, 1.5],
            "equal_weights": 0.2,
            "drop_one_metric": "Set each metric to zero in turn; normalize the remaining weights.",
            "normalization": "All weight vectors are nonnegative and normalized to sum to one.",
            "random": {"distribution": "Dirichlet(1,1,1,1,1)", "generator": "numpy.random.default_rng (PCG64)", "seed": RANDOM_SEED, "count": RANDOM_SCENARIO_COUNT},
            "flag_bonus": "Unchanged candidate-only bonus in every weight scenario; a separate flag_bonus_off scenario passes no metadata to the existing ranker, without changing catalog flags.",
            "tie_policy": "Existing rank_candidates order: descending rounded ACI, then descending base score, then stable catalog order. Use ordinal positions for Spearman, matching window_sensitivity.py; no average ranks for tied scores.",
            "summary_denominator": "All 1018 scenarios, including baseline and the separate bonus-off case; random-only summaries use the 1000 draws. Scenario percentages describe this chosen mix, not scientific probabilities.",
            "precision": "ACI is the unchanged ranker's two-decimal output; Spearman and stability percentages are rounded to six decimals; median uses the recorded Spearman values.",
            "baseline_check": "Both complete orders and every ACI must exactly equal the protected ranking JSONs before analysis output can be written.",
            "limitation": "Tests robustness to metric weights, not scientific correctness of the weights or flags; existing DEM resolution and physical-footprint mismatches remain.",
        },
        "site_count": len(candidates),
        "scenario_count_per_target": len(scenarios),
        "scenario_definitions": scenarios,
        "targets": target_results,
        "protected_ranking_sha256": final_hashes,
    }


def main():
    payload = build_payload()
    with OUTPUT_PATH.open("w", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, allow_nan=False)
        output.write("\n")
    print(f"Weight sensitivity: {OUTPUT_PATH}")
    for body, target in payload["targets"].items():
        summary = target["summary"]
        print(
            f"{body}: leader stays #1 in {summary['leader_retained_count']}/{summary['scenario_count']} "
            f"({summary['leader_stability_percent']}%); top 3 {summary['top3_stability_percent']}%; "
            f"leader changes: {len(summary['leader_changes'])}."
        )
    for filename, digest in payload["protected_ranking_sha256"].items():
        print(f"SHA-256 {filename}: {digest}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Weight sensitivity stopped: {error}") from error