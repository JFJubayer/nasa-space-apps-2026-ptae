import json
import math
import unittest
from pathlib import Path

import numpy as np

from src.analog_score import (
    auc_separation,
    composite_aci,
    environment_similarity,
    geology_similarity,
    robust_rank_statistics,
    terrain_similarity,
)
from src.geodata import grid_offsets, offsets_to_latlon
from src.multiscale import mask_water, sliding_windows, terrain_signature

ROOT = Path(__file__).resolve().parents[1]


def tilted_plane(angle_deg, size=200, spacing=120.0):
    x = np.arange(size) * spacing
    return np.tile(np.tan(np.radians(angle_deg)) * x, (size, 1))


class TestMultiscale(unittest.TestCase):
    def test_tilted_plane_recovers_slope_at_every_baseline(self):
        signature = terrain_signature(tilted_plane(7.0), 120.0)
        for median in signature["median_slope_deg"]:
            self.assertAlmostEqual(median, 7.0, places=3)
        self.assertAlmostEqual(signature["hurst"], 1.0, places=2)

    def test_flat_surface_has_zero_slope(self):
        signature = terrain_signature(np.zeros((150, 150)), 120.0)
        self.assertTrue(all(value == 0 for value in signature["median_slope_deg"]))

    def test_rough_surface_slope_falls_with_baseline(self):
        rng = np.random.default_rng(1)
        signature = terrain_signature(rng.normal(0, 5, (200, 200)), 120.0)
        self.assertGreater(signature["median_slope_deg"][0], signature["median_slope_deg"][-1])
        self.assertLess(signature["hurst"], 0.2)

    def test_nan_cells_are_ignored(self):
        dem = tilted_plane(4.0)
        dem[:60, :60] = np.nan
        signature = terrain_signature(dem, 120.0)
        self.assertAlmostEqual(signature["median_slope_deg"][0], 4.0, places=3)

    def test_mask_water_flags_sea_level_cells(self):
        dem = np.array([[-5.0, 10.0], [0.2, 30.0]])
        masked, fraction = mask_water(dem)
        self.assertEqual(fraction, 0.5)
        self.assertTrue(np.isnan(masked[0, 0]) and np.isnan(masked[1, 0]))

    def test_sliding_windows_cover_region_edges(self):
        region = np.zeros((100, 100))
        windows = list(sliding_windows(region, 40, 25))
        self.assertIn((60, 60), [(row, col) for row, col, _ in windows])
        self.assertTrue(all(window.shape == (40, 40) for _, _, window in windows))

    def test_grid_is_centered_and_metric(self):
        east, north = grid_offsets(10.0, 100.0)
        self.assertEqual(east.shape, (100, 100))
        self.assertAlmostEqual(float(east[0, 0]), -float(east[0, -1]))
        self.assertAlmostEqual(float(north[0, 0]), 4950.0)
        lat, lon = offsets_to_latlon(0.0, 10.0, east, north, 6371008.8)
        self.assertAlmostEqual(float(lat.max() - lat.min()), math.degrees(9900 / 6371008.8), places=6)


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.reference = terrain_signature(tilted_plane(5.0), 120.0)

    def test_identical_terrain_scores_one_and_distant_terrain_scores_low(self):
        self.assertAlmostEqual(terrain_similarity(self.reference, self.reference), 1.0)
        steep = terrain_signature(tilted_plane(25.0), 120.0)
        self.assertLess(terrain_similarity(self.reference, steep), 0.05)

    def test_valid_baselines_restrict_comparison(self):
        other = terrain_signature(tilted_plane(5.0), 120.0)
        self.assertAlmostEqual(terrain_similarity(self.reference, other, valid_baselines=[960, 1920]), 1.0)
        with self.assertRaises(ValueError):
            terrain_similarity(self.reference, other, valid_baselines=[7])

    def test_environment_similarity_peaks_at_target(self):
        target = {"t_mean_c": -50, "t_daily_range_c": 35, "precip_mm_yr": 0, "rel_humidity_pct": 5, "surface_pressure_kpa": 33}
        sigma = {k: 10.0 for k in target}
        score, per_feature = environment_similarity(target, target, sigma)
        self.assertEqual(score, 1.0)
        wet = dict(target, precip_mm_yr=2000)
        self.assertLess(environment_similarity(wet, target, sigma)[1]["precip_mm_yr"], 1e-6)

    def test_geology_similarity_is_weighted_recall(self):
        target = {"impact": 1, "polar_cold": 1, "ground_ice": 2}
        self.assertAlmostEqual(geology_similarity({"impact": 1, "ground_ice": 0.5}, target), (1 + 1) / 4)
        self.assertEqual(geology_similarity({}, target), 0.0)

    def test_geometric_aggregation_is_non_compensatory(self):
        additive = composite_aci(0.95, 0.02, 0.5, aggregation="additive")
        geometric = composite_aci(0.95, 0.02, 0.5, aggregation="geometric")
        self.assertLess(geometric, additive)
        self.assertAlmostEqual(composite_aci(1, 1, 1), 100.0)
        with self.assertRaises(ValueError):
            composite_aci(1, 1, 1, aggregation="median")

    def test_auc_separation(self):
        self.assertEqual(auc_separation([3, 4], [1, 2]), 1.0)
        self.assertEqual(auc_separation([1, 2], [3, 4]), 0.0)
        self.assertEqual(auc_separation([1], [1]), 0.5)

    def test_robust_ranks_are_stable_for_dominant_site(self):
        components = {
            "best": {"terrain_by_scale": [0.9, 0.9, 0.9], "environment": 0.9, "geology": 0.9},
            "weak": {"terrain_by_scale": [0.2, 0.2, 0.2], "environment": 0.2, "geology": 0.2},
        }
        stats = robust_rank_statistics(components, draws=100)
        self.assertEqual(stats["best"]["prob_top1"], 1.0)
        self.assertEqual(stats["weak"]["rank_p10"], 2)


class TestCatalogsAndResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sites = json.loads((ROOT / "catalog" / "earth_sites.json").read_text(encoding="utf-8"))
        cls.targets = json.loads((ROOT / "catalog" / "targets.json").read_text(encoding="utf-8"))

    def test_site_catalog_is_consistent(self):
        vocabulary = set(self.sites["tag_vocabulary"])
        ids = [site["id"] for site in self.sites["sites"]]
        self.assertEqual(len(ids), len(set(ids)))
        for site in self.sites["sites"]:
            self.assertIn(site["category"], {"benchmark", "emerging", "control"})
            self.assertTrue(-90 <= site["lat"] <= 90 and -180 <= site["lon"] <= 180)
            self.assertTrue(set(site["tags"]) <= vocabulary, site["id"])
            self.assertTrue(all(value in (0.5, 1) for value in site["tags"].values()), site["id"])
            self.assertTrue(site["heritage"] and site["limits"])
        categories = {site["category"] for site in self.sites["sites"]}
        self.assertEqual(categories, {"benchmark", "emerging", "control"})

    def test_target_catalog_is_consistent(self):
        vocabulary = set(self.sites["tag_vocabulary"])
        for target in self.targets["targets"]:
            self.assertIn(target["body"], {"moon", "mars"})
            self.assertTrue(set(target["tags"]) <= vocabulary, target["id"])
        self.assertEqual(set(self.targets["earth_floor"]) - {"note"}, set(self.targets["environment_sigma"]) - {"note"})

    def test_published_results_match_catalogs(self):
        results = json.loads((ROOT / "dashboard" / "global_results.json").read_text(encoding="utf-8"))
        self.assertEqual({s["id"] for s in results["sites"]}, {s["id"] for s in self.sites["sites"]})
        self.assertEqual({t["id"] for t in results["targets"]}, {t["id"] for t in self.targets["targets"]})
        for target in results["targets"]:
            ranks = [row["rank"] for row in target["rankings"]]
            self.assertEqual(ranks, list(range(1, len(self.sites["sites"]) + 1)))
            acis = [row["aci"] for row in target["rankings"]]
            self.assertEqual(acis, sorted(acis, reverse=True))
            if target["body"] == "mars":
                self.assertTrue(all(b >= results["method"]["mars_min_valid_baseline_m"] for b in target["valid_baselines_m"]))


if __name__ == "__main__":
    unittest.main()
