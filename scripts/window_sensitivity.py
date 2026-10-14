#!/usr/bin/env python3
"""Compare lunar analog rankings across small, centered DEM windows."""

import contextlib
import csv
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main
from scripts.prepare_real_data import prepare_geotiff

WINDOW_SIZES_KM = (5, 10, 15)
SYNTHETIC_EARTH_FILES = (
    "earth_atacama_puna.npy",
    "earth_mcmurdo_dry_valleys.npy",
    "earth_haughton_crater.npy",
    "earth_hawaii_mauna_kea.npy",
)


def build_comparison_table(window_results, window_sizes=WINDOW_SIZES_KM):
    """Build one wide, candidate-per-row table from per-window pipeline results."""
    candidate_names = {}
    for window_size in window_sizes:
        for result in window_results.get(window_size, {}).get("rankings", []):
            site_id = result["site_name"]
            candidate_names.setdefault(
                site_id,
                result.get("metadata", {}).get("name", site_id),
            )

    columns = ["candidate"]
    for window_size in window_sizes:
        suffix = f"{window_size}km"
        columns.extend((
            f"rank_{suffix}",
            f"base_{suffix}",
            f"bonus_{suffix}",
            f"final_aci_{suffix}",
            f"target_mean_slope_{suffix}",
            f"iceland_output_m_per_pixel_{suffix}",
            f"moon_output_m_per_pixel_{suffix}",
        ))

    rows = []
    for site_id, display_name in candidate_names.items():
        row = {"candidate": display_name}
        for window_size in window_sizes:
            suffix = f"{window_size}km"
            window = window_results.get(window_size, {})
            ranking = next(
                (item for item in window.get("rankings", []) if item["site_name"] == site_id),
                None,
            )
            row[f"rank_{suffix}"] = window.get("rankings", []).index(ranking) + 1 if ranking else None
            row[f"base_{suffix}"] = ranking.get("base_topographic_score") if ranking else None
            row[f"bonus_{suffix}"] = ranking.get("applied_bonus") if ranking else None
            row[f"final_aci_{suffix}"] = ranking.get("aci") if ranking else None
            row[f"target_mean_slope_{suffix}"] = window.get("target_mean_slope")
            row[f"iceland_output_m_per_pixel_{suffix}"] = window.get("iceland_resolution")
            row[f"moon_output_m_per_pixel_{suffix}"] = window.get("moon_resolution")
        rows.append(row)
    return columns, rows


def build_validation_payload(window_results, window_sizes=WINDOW_SIZES_KM):
    candidates = {}
    window_diagnostics = {}
    leaders_by_window = {}

    for window_size in window_sizes:
        key = str(window_size)
        window = window_results.get(window_size, {})
        rankings = window.get("rankings", [])
        if rankings:
            window_diagnostics[key] = {
                "target_mean_slope": window["target_mean_slope"],
                "iceland_output_ground_resolution_m_per_pixel": window["iceland_resolution"],
                "moon_output_ground_resolution_m_per_pixel": window["moon_resolution"],
            }
            leaders_by_window[key] = rankings[0].get("metadata", {}).get(
                "name", rankings[0]["site_name"]
            )
        else:
            window_diagnostics[key] = {"skipped": window.get("skipped_reason", "Window unavailable")}
            leaders_by_window[key] = None

        for rank, result in enumerate(rankings, 1):
            site_id = result["site_name"]
            candidate = candidates.setdefault(site_id, {
                "site_id": site_id,
                "name": result.get("metadata", {}).get("name", site_id),
                "windows": {},
            })
            candidate["windows"][key] = {
                "rank": rank,
                "base_topographic_score": result["base_topographic_score"],
                "applied_bonus": result["applied_bonus"],
                "final_aci": result["aci"],
            }

    comparable_leaders = [leader for leader in leaders_by_window.values() if leader is not None]
    rank_change = 0
    rank_change_candidate = None
    for candidate in candidates.values():
        ranks = [window["rank"] for window in candidate["windows"].values()]
        change = max(ranks) - min(ranks) if ranks else 0
        if change > rank_change:
            rank_change = change
            rank_change_candidate = candidate["name"]

    verdict = {
        "same_top_candidate_across_windows": (
            len(comparable_leaders) == len(window_sizes) and len(set(comparable_leaders)) == 1
        ),
        "leader_by_window": leaders_by_window,
        "largest_rank_change_places": rank_change,
        "largest_rank_change_candidate": rank_change_candidate,
    }
    return {
        "window_sizes_km": list(window_sizes),
        "candidates": list(candidates.values()),
        "window_diagnostics": window_diagnostics,
        "verdict": verdict,
    }


def format_comparison_table(window_results, columns, rows, window_sizes=WINDOW_SIZES_KM):
    """Render rank/ACI columns compactly and summarize per-window resolutions."""
    diagnostics = []
    for size in window_sizes:
        if not rows:
            continue
        row = rows[0]
        suffix = f"{size}km"
        slope = row.get(f"target_mean_slope_{suffix}")
        iceland_resolution = row.get(f"iceland_output_m_per_pixel_{suffix}")
        moon_resolution = row.get(f"moon_output_m_per_pixel_{suffix}")
        if slope is None:
            diagnostics.append(f"{size} km: skipped")
        else:
            diagnostics.append(
                f"{size} km: slope {slope:.2f} deg, Iceland {iceland_resolution:.2f}, "
                f"Moon {moon_resolution:.2f} m/px"
            )

    display_columns = ["Candidate"] + [f"{size} km rank/ACI" for size in window_sizes]
    display_rows = []
    for row in rows:
        cells = [row["candidate"]]
        for size in window_sizes:
            suffix = f"{size}km"
            rank = row[f"rank_{suffix}"]
            if rank is None:
                cells.append("SKIPPED")
                continue
            cells.append(f"#{rank} / {row[f'final_aci_{suffix}']:.2f}")
        display_rows.append(cells)

    widths = [
        max(len(display_columns[index]), *(len(row[index]) for row in display_rows))
        for index in range(len(display_columns))
    ]
    header = " | ".join(value.ljust(widths[index]) for index, value in enumerate(display_columns))
    rule = "-+-".join("-" * width for width in widths)
    body = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in display_rows
    ]
    return "Window diagnostics: " + "; ".join(diagnostics) + "\n" + "\n".join([header, rule, *body])


def _read_output_resolution(sidecar_path):
    with Path(sidecar_path).open(encoding="utf-8") as sidecar:
        return float(json.load(sidecar)["output_ground_resolution_m_per_pixel"])


def _prepare_window(source_dir, work_dir, window_size):
    try:
        _, iceland_sidecar = prepare_geotiff(
            source_dir / "earth_iceland_askja_srtm.tif",
            site="iceland",
            source_dataset="AWS Terrain Tiles (composite)",
            size=300,
            output_dir=work_dir,
            window_km=window_size,
            center_lat=65.0,
            center_lon=-16.7,
        )
    except ValueError as exc:
        if "extends outside the raster bounds" not in str(exc):
            raise
        return None, f"Skipping {window_size} km window for Iceland: {exc}"

    try:
        _, moon_sidecar = prepare_geotiff(
            source_dir / "luna_south_pole_lola_window.tif",
            site="moon",
            source_dataset="LRO LOLA South Polar DEM",
            size=300,
            output_dir=work_dir,
            window_km=window_size,
            center_lat=-90.0,
            center_lon=0.0,
        )
    except ValueError as exc:
        if "extends outside the raster bounds" not in str(exc):
            raise
        return None, f"Skipping {window_size} km window for Moon: {exc}"

    return {
        "iceland_resolution": _read_output_resolution(iceland_sidecar),
        "moon_resolution": _read_output_resolution(moon_sidecar),
    }, None


def run_sensitivity(data_dir=None, csv_path=None, json_path=None):
    source_dir = Path(data_dir) if data_dir else PROJECT_ROOT / "data"
    csv_path = Path(csv_path) if csv_path else PROJECT_ROOT / "results" / "window_sensitivity.csv"
    json_path = Path(json_path) if json_path else PROJECT_ROOT / "dashboard" / "window_sensitivity.json"
    required_sources = (
        "earth_iceland_askja_srtm.tif",
        "luna_south_pole_lola_window.tif",
        *SYNTHETIC_EARTH_FILES,
    )
    missing = [name for name in required_sources if not (source_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing window-sensitivity input(s) in '{source_dir}': {', '.join(missing)}"
        )

    window_results = {}
    with tempfile.TemporaryDirectory(prefix="ptae-window-sensitivity-") as temp_dir:
        work_dir = Path(temp_dir) / "data"
        work_dir.mkdir()
        for filename in SYNTHETIC_EARTH_FILES:
            shutil.copy2(source_dir / filename, work_dir / filename)

        for window_size in WINDOW_SIZES_KM:
            prepared, skip_message = _prepare_window(source_dir, work_dir, window_size)
            if skip_message:
                print(skip_message)
                window_results[window_size] = {"rankings": [], "skipped_reason": skip_message}
                continue

            target_path = work_dir / "target_moon_artemis_south_pole.npy"
            target_resolution = main._resolution_for_dem(str(target_path), use_existing_data=True)
            target_signature, _, _, _ = main.extract_terrain_signature(
                str(target_path), resolution=target_resolution
            )
            with contextlib.redirect_stdout(io.StringIO()):
                rankings = main.run_pipeline(
                    target_key="moon",
                    generate=False,
                    visualize=False,
                    output_dir=str(Path(temp_dir) / "pipeline-results"),
                    use_existing_data=True,
                    data_dir=str(work_dir),
                )

            window_results[window_size] = {
                "rankings": rankings,
                "target_mean_slope": target_signature["slope_mean"],
                **prepared,
            }

    columns, rows = build_comparison_table(window_results)
    print(format_comparison_table(window_results, columns, rows))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    validation_payload = build_validation_payload(window_results)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as json_file:
        json.dump(validation_payload, json_file, indent=2)
        json_file.write("\n")

    verdict = validation_payload["verdict"]
    comparable_leaders = [leader for leader in verdict["leader_by_window"].values() if leader is not None]
    leader_text = "yes" if verdict["same_top_candidate_across_windows"] else (
        "no" if len(comparable_leaders) == len(WINDOW_SIZES_KM) else "not comparable (window skipped)"
    )
    print(
        f"Verdict: same #1 candidate across all three windows: {leader_text}; "
        f"largest candidate rank change: {verdict['largest_rank_change_places']} place(s)."
    )
    print(f"CSV: {csv_path}")
    print(f"Dashboard JSON: {json_path}")
    return window_results, columns, rows


if __name__ == "__main__":
    run_sensitivity()