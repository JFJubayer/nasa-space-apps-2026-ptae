import json
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.weight_sensitivity import (
    METRICS,
    OUTPUT_PATH,
    RANDOM_SCENARIO_COUNT,
    RANDOM_SEED,
    assert_baseline_matches,
    build_payload,
    build_scenarios,
    spearman_rank_correlation,
    verify_protected_rankings,
)
from src.similarity_matcher import DEFAULT_WEIGHTS, rank_candidates


class TestWeightSensitivity(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[1]

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_baselines_equal_current_order_and_aci_for_both_targets(self):
        for body in ("moon", "mars"):
            with self.subTest(body=body):
                reference = json.loads((self.project_root / "dashboard" / f"results_{body}.json").read_text(encoding="utf-8"))
                expected = [{"site_id": row["site_id"], "aci": row["aci"]} for row in reference["rankings"]]
                ranked = rank_candidates(
                    reference["target_terrain_metrics"],
                    {row["site_id"]: row["terrain_metrics"] for row in reference["rankings"]},
                    weights=self.payload["scenario_definitions"][0]["weights"],
                    metadata={row["site_id"]: row["metadata"] for row in reference["rankings"]},
                )
                self.assertEqual([{"site_id": row["site_name"], "aci": row["aci"]} for row in ranked], expected)
                target = self.payload["targets"][body]
                self.assertEqual(target["baseline_ranking"], expected)
                baseline = target["scenarios"][0]
                self.assertEqual(baseline["scenario_id"], "baseline")
                self.assertEqual(baseline["leader_site_id"], expected[0]["site_id"])
                self.assertEqual(baseline["leader_aci"], expected[0]["aci"])
                self.assertEqual(baseline["top5_site_ids"], [row["site_id"] for row in expected[:5]])
                self.assertEqual(baseline["spearman_vs_baseline"], 1.0)

    def test_baseline_mismatch_stops_analysis_before_output(self):
        with patch("scripts.weight_sensitivity.load_signatures", return_value=({"moon": {}}, {}, {})), patch("scripts.weight_sensitivity.rank_candidates", return_value=[]):
            with self.assertRaisesRegex(ValueError, "Baseline mismatch for moon"):
                build_payload()
        with self.assertRaisesRegex(ValueError, "Baseline mismatch for mars"):
            assert_baseline_matches("mars", [])

    def test_all_scenario_weights_are_nonnegative_and_normalized(self):
        definitions = self.payload["scenario_definitions"]
        self.assertEqual(len(definitions), 1018)
        self.assertEqual(len({scenario["scenario_id"] for scenario in definitions}), 1018)
        for scenario in definitions:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(scenario["weights"]), set(METRICS))
                self.assertTrue(all(np.isfinite(weight) and weight >= 0 for weight in scenario["weights"].values()))
                self.assertLessEqual(abs(sum(scenario["weights"].values()) - 1.0), 1e-9)
                zero_count = sum(weight == 0 for weight in scenario["weights"].values())
                self.assertEqual(zero_count, 1 if scenario["family"] == "drop_one_metric" else 0)
                self.assertEqual(scenario["flag_bonus_enabled"], scenario["family"] != "flag_bonus_off")

    def test_random_weights_reproduce_fixed_seed(self):
        self.assertEqual(RANDOM_SEED, 42)
        self.assertEqual(build_scenarios(), build_scenarios(seed=42))
        random_rows = [scenario for scenario in build_scenarios() if scenario["family"] == "random"]
        different_seed = [scenario for scenario in build_scenarios(seed=43) if scenario["family"] == "random"]
        self.assertEqual(len(random_rows), 1000)
        self.assertNotEqual(random_rows, different_seed)

    def test_json_payload_schema_and_random_scenario_count(self):
        stored = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(stored, self.payload)
        self.assertEqual(stored["site_count"], 20)
        self.assertEqual(stored["scenario_count_per_target"], 1018)
        self.assertIn("protocol", stored)
        self.assertEqual(stored["protocol"]["random"]["count"], RANDOM_SCENARIO_COUNT)
        self.assertEqual(RANDOM_SCENARIO_COUNT, 1000)
        definitions = {scenario["scenario_id"]: scenario for scenario in stored["scenario_definitions"]}
        self.assertEqual(sum(row["family"] == "random" for row in definitions.values()), 1000)
        required = {"scenario_id", "leader_site_id", "leader_aci", "top5_site_ids", "spearman_vs_baseline", "baseline_leader_rank"}
        for target in stored["targets"].values():
            self.assertEqual(len(target["scenarios"]), 1018)
            self.assertEqual(sum(definitions[row["scenario_id"]]["family"] == "random" for row in target["scenarios"]), 1000)
            for scenario in target["scenarios"]:
                self.assertTrue(required.issubset(scenario))
                self.assertEqual(len(set(scenario["top5_site_ids"])), 5)
                self.assertEqual(scenario["top5_site_ids"][0], scenario["leader_site_id"])
                self.assertGreaterEqual(scenario["spearman_vs_baseline"], -1)
                self.assertLessEqual(scenario["spearman_vs_baseline"], 1)

    def test_summaries_and_complete_leader_change_lists_match_scenarios(self):
        for target in self.payload["targets"].values():
            rows = target["scenarios"]
            summary = target["summary"]
            leader = target["baseline_leader_site_id"]
            first_count = sum(row["leader_site_id"] == leader for row in rows)
            top_three_count = sum(row["baseline_leader_rank"] <= 3 for row in rows)
            self.assertEqual(summary["scenario_count"], len(rows))
            self.assertEqual(summary["leader_retained_count"], first_count)
            self.assertEqual(summary["top3_retained_count"], top_three_count)
            self.assertEqual(summary["leader_stability_percent"], round(100 * first_count / len(rows), 6))
            self.assertEqual(summary["top3_stability_percent"], round(100 * top_three_count / len(rows), 6))
            self.assertEqual(summary["min_spearman"], min(row["spearman_vs_baseline"] for row in rows))
            self.assertEqual(summary["median_spearman"], float(np.median([row["spearman_vs_baseline"] for row in rows])))
            self.assertEqual(
                summary["leader_changes"],
                [{"scenario_id": row["scenario_id"], "replacement_site_id": row["leader_site_id"], "replacement_aci": row["leader_aci"]} for row in rows if row["leader_site_id"] != leader],
            )

    def test_default_weights_remain_unchanged(self):
        expected = {"slope_mean": 0.30, "slope_std": 0.15, "tri_mean": 0.25, "tri_std": 0.15, "elevation_std": 0.15}
        self.assertEqual(DEFAULT_WEIGHTS, expected)
        self.assertEqual(self.payload["protocol"]["baseline_weights"], expected)
        self.assertEqual(self.payload["scenario_definitions"][0]["weights"], expected)

    def test_spearman_uses_stable_ranker_positions_for_ties(self):
        signature = dict.fromkeys(METRICS, 10.0)
        ranked = rank_candidates(signature, {"earth_z": signature, "earth_a": signature}, weights=dict(DEFAULT_WEIGHTS))
        order = [row["site_name"] for row in ranked]
        self.assertEqual(order, ["earth_z", "earth_a"])
        self.assertEqual(spearman_rank_correlation(order, order), 1.0)
        self.assertEqual(spearman_rank_correlation(order, list(reversed(order))), -1.0)
        with self.assertRaises(ValueError):
            spearman_rank_correlation(order, ["earth_z"])

    def test_protected_ranking_hashes_match(self):
        self.assertEqual(verify_protected_rankings(), self.payload["protected_ranking_sha256"])


if __name__ == "__main__":
    unittest.main()