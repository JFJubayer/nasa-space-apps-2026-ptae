import os
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import main
from src.terrain_metrics import calculate_slope, calculate_tri
from src.synthetic_generator import generate_all_datasets
from src.similarity_matcher import (
    compute_metric_similarity,
    calculate_analog_compatibility_index,
    rank_candidates,
)
from scripts.prepare_real_data import prepare_geotiff
from scripts.window_sensitivity import build_comparison_table

try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None
    from_origin = None

class TestPlanetaryAnalogEngine(unittest.TestCase):

    @staticmethod
    def _signature(value=10.0):
        return {
            "slope_mean": value,
            "slope_std": value,
            "tri_mean": value,
            "tri_std": value,
            "elevation_std": value
        }

    def test_target_site_catalog_has_approximate_coordinates_and_valid_matches(self):
        catalog = main.load_target_site_catalog()
        sites_by_id = {site["id"]: site for site in catalog["target_sites"]}

        self.assertEqual(len(sites_by_id), 10)
        self.assertTrue(all(site["coords_approximate"] is True for site in sites_by_id.values()))
        for body, matches in catalog["analog_matches"].items():
            self.assertEqual(len(matches), 5)
            for match in matches:
                target = sites_by_id[match["target_site_id"]]
                self.assertEqual(target["body"].lower(), body)
                self.assertTrue(set(match["shared_features"]).issubset(target["key_features"]))
        self.assertNotEqual(
            [match["earth_analog_id"] for match in catalog["analog_matches"]["mars"]],
            [match["earth_analog_id"] for match in catalog["analog_matches"]["moon"]],
        )

    def test_ranked_json_includes_qualitative_target_catalog_without_changing_scores(self):
        catalog = main.load_target_site_catalog()
        signature = self._signature()
        site_id = "earth_atacama_puna"
        score = 72.0
        rankings = [{
            "site_name": site_id,
            "metadata": {"name": "Puna de Atacama"},
            "base_topographic_score": 70.0,
            "applied_bonus": 2.0,
            "aci": score,
            "capped": False,
            "sub_scores": {metric: 80.0 for metric in main.ACI_METRICS},
        }]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "results_mars.json"
            main.export_ranked_results(
                "mars", "Mars", signature, rankings, {site_id: signature}, str(output_path), catalog
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(payload["target_sites"]), 6)
        self.assertEqual(len(payload["analog_matches"]), 5)
        self.assertEqual(payload["rankings"][0]["aci"], score)

    def test_flat_terrain_slope_and_tri(self):
        """A completely flat DEM should yield 0 slope and 0 TRI."""
        flat_dem = np.ones((20, 20)) * 500.0
        slope = calculate_slope(flat_dem, resolution=30.0)
        tri = calculate_tri(flat_dem)
        
        self.assertAlmostEqual(float(np.mean(slope)), 0.0, places=4)
        self.assertAlmostEqual(float(np.mean(tri)), 0.0, places=4)

    def test_tilted_plane_slope(self):
        """A uniform linear ramp should calculate an exact expected slope."""
        # 30m resolution, 30m vertical rise per cell along X axis -> arctan(1) = 45 degrees
        x = np.arange(20) * 30.0
        tilted_dem = np.tile(x, (20, 1)).astype(float)
        slope = calculate_slope(tilted_dem, resolution=30.0)
        
        # Central interior cells (away from edge artifacts)
        interior_slope = slope[2:-2, 2:-2]
        self.assertAlmostEqual(float(np.mean(interior_slope)), 45.0, places=1)

    def test_identical_signatures_yield_100_percent_aci(self):
        """Identical signatures must result in an ACI score of 100%."""
        sig = {
            "slope_mean": 15.0,
            "slope_std": 5.0,
            "tri_mean": 8.0,
            "tri_std": 3.0,
            "elevation_std": 200.0
        }
        res = calculate_analog_compatibility_index(sig, sig)
        self.assertEqual(res["aci"], 100.0)

    def test_divergent_signatures_yield_lower_score(self):
        """Divergent terrain characteristics should have lower similarity."""
        target_sig = {
            "slope_mean": 25.0,
            "slope_std": 10.0,
            "tri_mean": 18.0,
            "tri_std": 6.0,
            "elevation_std": 500.0
        }
        dissimilar_sig = {
            "slope_mean": 1.0,
            "slope_std": 0.5,
            "tri_mean": 0.2,
            "tri_std": 0.1,
            "elevation_std": 10.0
        }
        res = calculate_analog_compatibility_index(target_sig, dissimilar_sig)
        self.assertLess(res["aci"], 50.0)

    def test_metric_similarity_bounds(self):
        """Similarity is bounded inclusively between 0 and 1."""
        self.assertEqual(compute_metric_similarity(10.0, 10.0), 1.0)
        self.assertEqual(compute_metric_similarity(10.0, 1_000_000.0), 0.0)

    def test_similarity_rejects_nonfinite_values_and_keeps_tolerance_fallback(self):
        for invalid_value in (np.nan, np.inf, -np.inf):
            for argument in ("target_val", "candidate_val", "tolerance_scale"):
                values = {
                    "target_val": 10.0,
                    "candidate_val": 12.0,
                    "tolerance_scale": 1.0
                }
                values[argument] = invalid_value
                with self.subTest(argument=argument, value=invalid_value):
                    with self.assertRaises(ValueError):
                        compute_metric_similarity(**values)

        self.assertEqual(compute_metric_similarity(10.0, 10.0, tolerance_scale=0), 1.0)
        self.assertEqual(compute_metric_similarity(10.0, 10.0, tolerance_scale=-2), 1.0)

    def test_aci_rejects_missing_required_metrics(self):
        for signature_name in ("target", "candidate"):
            for metric in self._signature():
                target_sig = self._signature()
                candidate_sig = self._signature()
                signature = target_sig if signature_name == "target" else candidate_sig
                del signature[metric]
                with self.subTest(signature=signature_name, metric=metric):
                    with self.assertRaisesRegex(ValueError, "missing required metric"):
                        calculate_analog_compatibility_index(target_sig, candidate_sig)

    def test_aci_rejects_nonfinite_and_negative_terrain_metrics(self):
        for metric in self._signature():
            for invalid_value in (np.nan, np.inf, -np.inf, -1.0):
                for signature_name in ("target", "candidate"):
                    target_sig = self._signature()
                    candidate_sig = self._signature()
                    signature = target_sig if signature_name == "target" else candidate_sig
                    signature[metric] = invalid_value
                    with self.subTest(metric=metric, value=invalid_value, signature=signature_name):
                        with self.assertRaises(ValueError):
                            calculate_analog_compatibility_index(target_sig, candidate_sig)

    def test_aci_rejects_invalid_weights(self):
        invalid_weights = (
            {"slope_mean": -1.0},
            {"slope_mean": np.nan},
            {"slope_mean": np.inf},
            {"unknown_metric": 1.0},
            {"slope_mean": 0.0},
            {},
            {"slope_mean": 1e308, "slope_std": 1e308},
        )
        signature = self._signature()
        for weights in invalid_weights:
            with self.subTest(weights=weights):
                with self.assertRaises(ValueError):
                    calculate_analog_compatibility_index(signature, signature, weights=weights)

    def test_valid_partial_custom_weights_are_normalized(self):
        signature = self._signature()
        result = calculate_analog_compatibility_index(
            signature, signature, weights={"slope_mean": 2.0, "tri_mean": 1.0}
        )
        scaled_result = calculate_analog_compatibility_index(
            signature, signature, weights={"slope_mean": 20.0, "tri_mean": 10.0}
        )

        self.assertEqual(result["aci"], 100.0)
        self.assertEqual(result["aci"], scaled_result["aci"])
        self.assertEqual(set(result["sub_scores"]), {"slope_mean", "tri_mean"})

    def test_environmental_bonuses_and_missing_flags(self):
        target_sig = self._signature(10.0)
        candidate_sig = self._signature(15.0)
        base_similarity = float(np.exp(-0.5))
        expected_base = round(base_similarity * 100.0, 2)
        flag_sets = (
            {},
            {"is_hyper_arid": True},
            {"is_basaltic": True},
            {"has_lava_tubes": True},
            {"is_hyper_arid": True, "is_basaltic": True, "has_lava_tubes": True},
        )

        for flags in flag_sets:
            result = rank_candidates(
                target_sig,
                {"candidate": candidate_sig},
                metadata={"candidate": flags},
            )[0]
            expected_bonus = round(5.0 * sum(flags.values()) / 3.0, 2)
            expected_score = round(expected_base + expected_bonus, 2)
            with self.subTest(flags=flags):
                self.assertEqual(result["aci"], expected_score)
                self.assertEqual(result["base_topographic_score"], expected_base)
                self.assertEqual(result["applied_bonus"], expected_bonus)
                self.assertFalse(result["capped"])

    def test_mauna_kea_metadata_bonus_and_final_aci_cap(self):
        target_sig = {"slope_mean": 10.0}
        metadata = {
            "earth_hawaii_mauna_kea": {
                "is_basaltic": True,
                "has_lava_tubes": True,
                "is_hyper_arid": False,
            }
        }
        weights = {"slope_mean": 1.0}

        imperfect = rank_candidates(
            target_sig,
            {"earth_hawaii_mauna_kea": {"slope_mean": 15.0}},
            weights=weights,
            metadata=metadata,
        )[0]
        expected_base = round(float(np.exp(-0.5)) * 100.0, 2)
        self.assertEqual(imperfect["base_topographic_score"], expected_base)
        self.assertLess(imperfect["base_topographic_score"], 100.0)
        self.assertEqual(imperfect["applied_bonus"], 3.33)
        self.assertEqual(imperfect["aci"], round(expected_base + imperfect["applied_bonus"], 2))
        self.assertFalse(imperfect["capped"])

        near_match = rank_candidates(
            target_sig,
            {"earth_hawaii_mauna_kea": {"slope_mean": 11.0}},
            weights=weights,
            metadata=metadata,
        )[0]
        expected_near_base = round(float(np.exp(-0.5 * (1.0 / 5.0) ** 2)) * 100.0, 2)
        self.assertEqual(near_match["base_topographic_score"], expected_near_base)
        self.assertLess(near_match["base_topographic_score"], 100.0)
        self.assertEqual(near_match["applied_bonus"], round(near_match["aci"] - expected_near_base, 2))
        self.assertLess(near_match["applied_bonus"], 3.33)
        self.assertEqual(near_match["aci"], 99.99)
        self.assertTrue(near_match["capped"])

    def test_different_high_base_scores_remain_distinguishable_after_bonus(self):
        target_sig = {"slope_mean": 10.0}
        mauna_flags = {"is_basaltic": True, "has_lava_tubes": True}
        candidates = {
            "mauna_kea_exact": {"slope_mean": 10.0},
            "mauna_kea_near": {"slope_mean": 11.0},
        }
        metadata = {site: mauna_flags for site in candidates}

        rankings = rank_candidates(
            target_sig,
            candidates,
            weights={"slope_mean": 1.0},
            metadata=metadata,
        )
        base_scores = {result["site_name"]: result["base_topographic_score"] for result in rankings}
        final_scores = {result["site_name"]: result["aci"] for result in rankings}

        self.assertNotEqual(base_scores["mauna_kea_exact"], base_scores["mauna_kea_near"])
        self.assertEqual(base_scores, {"mauna_kea_exact": 100.0, "mauna_kea_near": 98.02})
        self.assertEqual(final_scores, {"mauna_kea_exact": 100.0, "mauna_kea_near": 99.99})
        self.assertEqual(
            {result["site_name"]: result["applied_bonus"] for result in rankings},
            {"mauna_kea_exact": 0.0, "mauna_kea_near": 1.97},
        )
        self.assertTrue(all(result["capped"] for result in rankings))
        self.assertEqual([result["site_name"] for result in rankings], ["mauna_kea_exact", "mauna_kea_near"])

    def test_rank_candidates_rejects_nonboolean_environmental_flags(self):
        signature = self._signature()
        for invalid_flag in (1, "true", None):
            with self.subTest(flag_value=invalid_flag):
                with self.assertRaisesRegex(ValueError, "must be boolean"):
                    rank_candidates(
                        signature,
                        {"candidate": signature},
                        metadata={"candidate": {"is_basaltic": invalid_flag}},
                    )

    def test_aci_rejects_invalid_environmental_boost(self):
        signature = self._signature()
        for invalid_boost in (-0.01, 5.01, np.nan, np.inf, -np.inf):
            with self.subTest(boost=invalid_boost):
                with self.assertRaises(ValueError):
                    calculate_analog_compatibility_index(
                        signature, signature, environmental_boost=invalid_boost
                    )

    def test_aci_score_cap_and_rounding(self):
        signature = self._signature()
        capped = calculate_analog_compatibility_index(
            signature, signature, environmental_boost=1.0
        )
        target_sig = self._signature(10.0)
        candidate_sig = self._signature(15.0)
        rounded = calculate_analog_compatibility_index(
            target_sig,
            candidate_sig,
            weights={"slope_mean": 1.0},
        )

        self.assertEqual(capped["aci"], 100.0)
        self.assertEqual(capped["base_topographic_score"], 100.0)
        self.assertEqual(capped["applied_bonus"], 0.0)
        self.assertTrue(capped["capped"])
        self.assertEqual(rounded["aci"], 60.65)
        self.assertEqual(rounded["sub_scores"]["slope_mean"], 60.7)

    def test_rank_candidates_orders_by_descending_aci_and_preserves_ties(self):
        target_sig = self._signature()
        candidates = {
            "dissimilar": self._signature(1000.0),
            "exact": self._signature(),
            "moderate": self._signature(15.0),
        }
        rankings = rank_candidates(target_sig, candidates)
        self.assertEqual(
            [result["site_name"] for result in rankings],
            ["exact", "moderate", "dissimilar"],
        )

        tied_rankings = rank_candidates(
            target_sig,
            {"first": target_sig, "second": target_sig.copy()},
        )
        self.assertEqual(
            [result["site_name"] for result in tied_rankings],
            ["first", "second"],
        )


class TestPipelineDataModes(unittest.TestCase):

    def test_use_existing_data_reports_missing_required_file(self):
        original_cwd = os.getcwd()
        temp_dir = tempfile.TemporaryDirectory()
        try:
            try:
                os.chdir(temp_dir.name)
                dataset_paths, _ = generate_all_datasets(data_dir="data", generate=False)
                missing_path = next(
                    path for path in dataset_paths
                    if os.path.basename(path) == "earth_atacama_puna.npy"
                )
                for path in dataset_paths:
                    if path != missing_path and os.path.basename(path).startswith("earth_"):
                        Path(path).touch()
                Path("data/target_moon_artemis_south_pole.npy").touch()

                with self.assertRaisesRegex(FileNotFoundError, "earth_atacama_puna\\.npy"):
                    main.run_pipeline(use_existing_data=True, visualize=False)
            finally:
                os.chdir(original_cwd)
        finally:
            temp_dir.cleanup()

    def test_use_existing_data_loads_required_files_without_generation(self):
        original_cwd = os.getcwd()
        temp_dir = tempfile.TemporaryDirectory()
        try:
            try:
                os.chdir(temp_dir.name)
                dataset_paths, _ = generate_all_datasets(data_dir="data", generate=False)
                candidate_paths = [
                    path for path in dataset_paths
                    if os.path.basename(path).startswith("earth_")
                ]
                moon_target = "data/target_moon_artemis_south_pole.npy"
                expected_paths = [moon_target] + candidate_paths
                for path in expected_paths:
                    Path(path).touch()

                signature = {
                    "slope_mean": 1.0,
                    "slope_std": 0.5,
                    "tri_mean": 1.0,
                    "tri_std": 0.5,
                    "elevation_std": 10.0,
                    "elevation_min": 0.0,
                    "elevation_max": 10.0,
                }
                extracted = (signature, np.zeros((2, 2)), np.zeros((2, 2)), np.zeros((2, 2)))
                ranking = [{
                    "site_name": "earth_iceland_askja",
                    "metadata": {"name": "Askja", "type": "Test site"},
                    "aci": 75.0,
                    "base_topographic_score": 73.0,
                    "applied_bonus": 2.0,
                    "capped": False,
                    "sub_scores": {},
                }]

                with patch("main.generate_all_datasets", wraps=generate_all_datasets) as dataset_loader:
                    with patch("main.extract_terrain_signature", return_value=extracted) as extract:
                        with patch("main.rank_candidates", return_value=ranking):
                            main.run_pipeline(use_existing_data=True, visualize=False)

                dataset_loader.assert_called_once_with(data_dir="data", generate=False)
                loaded_files = {os.path.basename(call.args[0]) for call in extract.call_args_list}
                self.assertEqual(loaded_files, {os.path.basename(path) for path in expected_paths})
                self.assertFalse(Path("data/target_mars_jezero_crater.npy").exists())
            finally:
                os.chdir(original_cwd)
        finally:
            temp_dir.cleanup()

    def test_default_run_still_generates_synthetic_datasets(self):
        original_cwd = os.getcwd()
        temp_dir = tempfile.TemporaryDirectory()
        try:
            try:
                os.chdir(temp_dir.name)
                signature = {
                    "slope_mean": 1.0,
                    "slope_std": 0.5,
                    "tri_mean": 1.0,
                    "tri_std": 0.5,
                    "elevation_std": 10.0,
                    "elevation_min": 0.0,
                    "elevation_max": 10.0,
                }
                extracted = (signature, np.zeros((2, 2)), np.zeros((2, 2)), np.zeros((2, 2)))
                ranking = [{
                    "site_name": "earth_iceland_askja",
                    "metadata": {"name": "Askja", "type": "Test site"},
                    "aci": 75.0,
                    "base_topographic_score": 73.0,
                    "applied_bonus": 2.0,
                    "capped": False,
                    "sub_scores": {},
                }]

                with patch("main.extract_terrain_signature", return_value=extracted), patch(
                    "main.rank_candidates", return_value=ranking
                ):
                    main.run_pipeline(visualize=False)

                expected_files = {
                    "target_moon_artemis_south_pole.npy",
                    "target_mars_jezero_crater.npy",
                    "earth_iceland_askja.npy",
                    "earth_atacama_puna.npy",
                    "earth_mcmurdo_dry_valleys.npy",
                    "earth_haughton_crater.npy",
                    "earth_hawaii_mauna_kea.npy",
                }
                self.assertEqual(set(os.listdir("data")), expected_files)
            finally:
                os.chdir(original_cwd)
        finally:
            temp_dir.cleanup()

    def test_cli_forwards_use_existing_data_flag(self):
        with patch.object(
            sys, "argv", ["main.py", "--use-existing-data", "--data-dir", "data_real"]
        ), patch(
            "main.run_pipeline"
        ) as run_pipeline:
            main.main()

        self.assertTrue(run_pipeline.call_args.kwargs["use_existing_data"])
        self.assertEqual(run_pipeline.call_args.kwargs["data_dir"], "data_real")


class TestRealDataPreparation(unittest.TestCase):

    @unittest.skipIf(rasterio is None, "rasterio is not installed; skipping GeoTIFF conversion test")
    def test_geotiff_converts_to_expected_npy_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "tiny_dem.tif"
            profile = {
                "driver": "GTiff",
                "height": 4,
                "width": 6,
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:32633",
                "transform": from_origin(500000, 5200000, 30, 30),
            }
            expected_dem = np.arange(24, dtype=np.float32).reshape(4, 6)
            with rasterio.open(input_path, "w", **profile) as dataset:
                dataset.write(expected_dem, 1)

            output_path, sidecar_path = prepare_geotiff(
                input_path,
                site="iceland",
                source_dataset="Test SRTM DEM",
                size=5,
                output_dir=temp_path / "data",
            )

            self.assertEqual(output_path.name, "earth_iceland_askja.npy")
            converted = np.load(output_path)
            self.assertEqual(converted.shape, (5, 5))
            self.assertTrue(np.isfinite(converted).all())
            with sidecar_path.open(encoding="utf-8") as sidecar:
                metadata = json.load(sidecar)
            self.assertEqual(metadata["source_dataset"], "Test SRTM DEM")
            self.assertAlmostEqual(metadata["original_ground_resolution_m_per_pixel"], 30.012, delta=0.01)
            self.assertAlmostEqual(metadata["output_ground_resolution_m_per_pixel"], 29.41, delta=0.05)
            self.assertAlmostEqual(metadata["center_lat"], 46.951, delta=0.01)
            self.assertAlmostEqual(metadata["center_lon"], 15.001, delta=0.01)
            self.assertEqual(metadata["bounds"]["left"], 500000.0)
            self.assertEqual(metadata["bounds"]["bottom"], 5199880.0)
            self.assertEqual(metadata["bounds"]["right"], 500180.0)
            self.assertEqual(metadata["bounds"]["top"], 5200000.0)

    @unittest.skipIf(rasterio is None, "rasterio is not installed; skipping GeoTIFF conversion test")
    def test_geographic_resolution_is_converted_to_meters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "geographic_dem.tif"
            profile = {
                "driver": "GTiff",
                "height": 4,
                "width": 6,
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:4326",
                "transform": from_origin(-16.75, 65.03, 1 / 3600, 1 / 3600),
            }
            with rasterio.open(input_path, "w", **profile) as dataset:
                dataset.write(np.arange(24, dtype=np.float32).reshape(4, 6), 1)

            _, sidecar_path = prepare_geotiff(
                input_path,
                site="iceland",
                source_dataset="Test SRTM DEM",
                size=5,
                output_dir=temp_path / "data",
            )

            with sidecar_path.open(encoding="utf-8") as sidecar:
                resolution = json.load(sidecar)["original_ground_resolution_m_per_pixel"]
            self.assertGreater(resolution, 20.0)
            self.assertLess(resolution, 35.0)

    @unittest.skipIf(rasterio is None, "rasterio is not installed; skipping GeoTIFF conversion test")
    def test_mercator_ground_resolution_corrects_for_latitude(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "mercator_dem.tif"
            from rasterio.warp import transform

            center_x, center_y = transform("EPSG:4326", "EPSG:3857", [0.0], [65.0])
            profile = {
                "driver": "GTiff",
                "height": 4,
                "width": 6,
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:3857",
                "transform": from_origin(center_x[0] - 3 * 76.44, center_y[0] + 2 * 76.44, 76.44, 76.44),
            }
            with rasterio.open(input_path, "w", **profile) as dataset:
                dataset.write(np.ones((4, 6), dtype=np.float32), 1)

            _, sidecar_path = prepare_geotiff(
                input_path,
                site="iceland",
                source_dataset="Test Web Mercator DEM",
                size=4,
                output_dir=temp_path / "data",
            )

            with sidecar_path.open(encoding="utf-8") as sidecar:
                metadata = json.load(sidecar)
            self.assertAlmostEqual(metadata["original_ground_resolution_m_per_pixel"], 32.3, delta=1.0)
            self.assertAlmostEqual(metadata["center_lat"], 65.0, delta=0.01)

    @unittest.skipIf(rasterio is None, "rasterio is not installed; skipping GeoTIFF crop test")
    def test_window_crop_is_centered_on_requested_coordinates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "mars_global.tif"
            from rasterio.warp import transform

            center_x, center_y = transform("EPSG:4326", "EPSG:3857", [77.7], [18.4])
            profile = {
                "driver": "GTiff",
                "height": 500,
                "width": 500,
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:3857",
                "transform": from_origin(center_x[0] - 250000, center_y[0] + 250000, 1000, 1000),
            }
            with rasterio.open(input_path, "w", **profile) as dataset:
                dataset.write(np.tile(np.arange(500, dtype=np.float32), (500, 1)), 1)

            output_path, sidecar_path = prepare_geotiff(
                input_path,
                site="mars",
                source_dataset="Global MOLA DEM",
                size=20,
                window_km=100,
                center_lat=18.4,
                center_lon=77.7,
                output_dir=temp_path / "data",
            )

            cropped = np.load(output_path)
            with sidecar_path.open(encoding="utf-8") as sidecar:
                metadata = json.load(sidecar)
            self.assertEqual(cropped.shape, (20, 20))
            self.assertAlmostEqual(float(np.mean(cropped)), 250.0, delta=2.0)
            self.assertEqual(metadata["center_lat"], 18.4)
            self.assertEqual(metadata["center_lon"], 77.7)
            self.assertGreater(metadata["output_ground_resolution_m_per_pixel"], 4900)
            self.assertLess(metadata["output_ground_resolution_m_per_pixel"], 5100)

            with self.assertRaisesRegex(ValueError, "extends outside the raster bounds"):
                prepare_geotiff(
                    input_path,
                    site="mars",
                    source_dataset="Global MOLA DEM",
                    size=20,
                    window_km=100,
                    center_lat=18.4,
                    center_lon=100.0,
                    output_dir=temp_path / "outside",
                )

    @unittest.skipIf(rasterio is None, "rasterio is not installed; skipping planetary CRS crop test")
    def test_mars_geographic_crop_uses_mars_radius(self):
        from rasterio.crs import CRS

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "mars_sphere.tif"
            mars_crs = CRS.from_proj4("+proj=longlat +R=3396190 +no_defs")
            profile = {
                "driver": "GTiff",
                "height": 150,
                "width": 100,
                "count": 1,
                "dtype": "float32",
                "crs": mars_crs,
                "transform": from_origin(70, 25, 0.1, 0.1),
            }
            with rasterio.open(input_path, "w", **profile) as dataset:
                dataset.write(np.ones((150, 100), dtype=np.float32), 1)

            output_path, sidecar_path = prepare_geotiff(
                input_path,
                site="mars",
                source_dataset="Global MOLA DEM",
                size=10,
                window_km=100,
                center_lat=18.4,
                center_lon=77.7,
                output_dir=temp_path / "data",
            )

            self.assertEqual(np.load(output_path).shape, (10, 10))
            with sidecar_path.open(encoding="utf-8") as sidecar:
                metadata = json.load(sidecar)
            self.assertGreater(metadata["original_ground_resolution_m_per_pixel"], 5000)
            self.assertLess(metadata["original_ground_resolution_m_per_pixel"], 6500)
            self.assertEqual(metadata["center_lat"], 18.4)
            self.assertEqual(metadata["center_lon"], 77.7)

    def test_existing_data_sidecar_resolution_is_passed_to_terrain_loader(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data_real"
            dataset_paths, _ = generate_all_datasets(data_dir=str(data_dir), generate=False)
            target_path = Path(dataset_paths[0])
            earth_paths = [Path(path) for path in dataset_paths if Path(path).name.startswith("earth_")]
            for path in [target_path] + earth_paths:
                path.touch()

            for path, resolution in ((target_path, 42.5), (earth_paths[0], 55.25)):
                with path.with_suffix(".json").open("w", encoding="utf-8") as sidecar:
                    json.dump({"output_ground_resolution_m_per_pixel": resolution}, sidecar)

            signature = {
                "slope_mean": 1.0,
                "slope_std": 0.5,
                "tri_mean": 1.0,
                "tri_std": 0.5,
                "elevation_std": 10.0,
                "elevation_min": 0.0,
                "elevation_max": 10.0,
            }
            extracted = (signature, np.zeros((2, 2)), np.zeros((2, 2)), np.zeros((2, 2)))
            ranking = [{
                "site_name": "earth_iceland_askja",
                "metadata": {"name": "Askja", "type": "Test site"},
                "aci": 75.0,
                "base_topographic_score": 73.0,
                "applied_bonus": 2.0,
                "capped": False,
                "sub_scores": {},
            }]

            with patch("main.extract_terrain_signature", return_value=extracted) as extract:
                with patch("main.rank_candidates", return_value=ranking):
                    main.run_pipeline(
                        use_existing_data=True,
                        data_dir=str(data_dir),
                        output_dir=str(Path(temp_dir) / "results"),
                        visualize=False,
                    )

            resolutions = {
                Path(call.args[0]).name: call.kwargs["resolution"]
                for call in extract.call_args_list
            }
            self.assertEqual(resolutions[target_path.name], 42.5)
            self.assertEqual(resolutions[earth_paths[0].name], 55.25)
            for path in earth_paths[1:]:
                self.assertEqual(resolutions[path.name], 30.0)


class TestWindowSensitivityTable(unittest.TestCase):

    def test_builds_candidate_rows_and_window_metrics(self):
        window_results = {
            5: {
                "rankings": [{
                    "site_name": "earth_askja",
                    "metadata": {"name": "Askja"},
                    "base_topographic_score": 70.0,
                    "applied_bonus": 1.67,
                    "aci": 71.67,
                }],
                "target_mean_slope": 12.5,
                "iceland_resolution": 16.7,
                "moon_resolution": 16.7,
            },
            10: {
                "rankings": [{
                    "site_name": "earth_mcmurdo",
                    "metadata": {"name": "McMurdo"},
                    "base_topographic_score": 80.0,
                    "applied_bonus": 1.67,
                    "aci": 81.67,
                }, {
                    "site_name": "earth_askja",
                    "metadata": {"name": "Askja"},
                    "base_topographic_score": 70.0,
                    "applied_bonus": 1.67,
                    "aci": 71.67,
                }],
                "target_mean_slope": 13.5,
                "iceland_resolution": 33.3,
                "moon_resolution": 33.3,
            },
        }

        columns, rows = build_comparison_table(window_results, window_sizes=(5, 10))
        rows_by_candidate = {row["candidate"]: row for row in rows}

        self.assertEqual(rows_by_candidate["Askja"]["rank_5km"], 1)
        self.assertEqual(rows_by_candidate["Askja"]["final_aci_5km"], 71.67)
        self.assertIsNone(rows_by_candidate["McMurdo"]["rank_5km"])
        self.assertEqual(rows_by_candidate["McMurdo"]["rank_10km"], 1)
        self.assertEqual(rows_by_candidate["Askja"]["target_mean_slope_10km"], 13.5)
        self.assertEqual(rows_by_candidate["Askja"]["iceland_output_m_per_pixel_10km"], 33.3)
        self.assertIn("moon_output_m_per_pixel_10km", columns)

if __name__ == "__main__":
    unittest.main()
