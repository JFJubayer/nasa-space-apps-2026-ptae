import unittest
import numpy as np
from src.terrain_metrics import calculate_slope, calculate_tri
from src.similarity_matcher import compute_metric_similarity, calculate_analog_compatibility_index

class TestPlanetaryAnalogEngine(unittest.TestCase):

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
        """Similarity score must always be bounded strictly between 0 and 1."""
        sim = compute_metric_similarity(10.0, 50.0)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)

if __name__ == "__main__":
    unittest.main()
