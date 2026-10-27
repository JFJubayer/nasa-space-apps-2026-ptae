import json
import re
import unittest
from pathlib import Path


class TestSubmissionPolish(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[1]

    def test_readme_top_summary_and_reading_guide(self):
        text = (self.project_root / "README.md").read_text(encoding="utf-8")
        blocks = re.split(r"\n\s*\n", text)
        summary = blocks[0]
        self.assertLessEqual(len(summary.splitlines()), 6)
        for phrase in ("PTAE", "20 real-DEM Earth candidates", "Teide", "Kilauea", "Prototype heuristic", "terrain morphology only", "not geology or mission suitability"):
            self.assertIn(phrase, summary)
        guide = next(block for block in blocks if block.startswith("**How to read the results:**"))
        self.assertLessEqual(len(guide.splitlines()), 5)
        for phrase in ("heuristic similarity score", "Moon leader is stable", "Mars leader is weight-sensitive"):
            self.assertIn(phrase, guide)

    def test_weight_card_loads_json_and_silently_hides_on_failure(self):
        html = (self.project_root / "dashboard/index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'id="weight-stability-card"[^>]*\bhidden')
        self.assertIn("#weight-stability-card[hidden] { display: none; }", html)
        loader = html.split("async function loadWeightStability() {", 1)[1].split("async function loadWindowSensitivity()", 1)[0]
        self.assertIn("fetch('weight_sensitivity.json'", loader)
        self.assertIn("if (!response.ok) return;", loader)
        self.assertIn("Number.isFinite(summary.leader_stability_percent)", loader)
        self.assertIn("Number.isFinite(summary.top3_stability_percent)", loader)
        self.assertRegex(loader, r"catch\s*\{\s*card\.hidden = true;")
        self.assertIn("card.hidden = false;", loader)
        self.assertNotIn("console.", loader)
        self.assertIn("Tests weight robustness, not scientific correctness of weights", html)

    def test_submission_robustness_numbers_equal_json(self):
        payload = json.loads((self.project_root / "dashboard/weight_sensitivity.json").read_text(encoding="utf-8"))
        text = (self.project_root / "NASA_SPACE_APPS_SUBMISSION.md").read_text(encoding="utf-8")
        paragraphs = [line for line in text.splitlines() if line.startswith("**Weight robustness:**")]
        self.assertEqual(len(paragraphs), 1)
        paragraph = paragraphs[0]
        match = re.search(r"Moon Teide stays #1 in ([\d.]+)% of ([\d,]+) scenarios \(top-3: ([\d.]+)%\); Mars Kilauea stays #1 in ([\d.]+)% \(top-3: ([\d.]+)%\)", paragraph)
        self.assertIsNotNone(match)
        moon = payload["targets"]["moon"]["summary"]
        mars = payload["targets"]["mars"]["summary"]
        self.assertEqual(match.group(1), f"{moon['leader_stability_percent']:.2f}")
        self.assertEqual(int(match.group(2).replace(",", "")), moon["scenario_count"])
        self.assertEqual(float(match.group(3)), round(moon["top3_stability_percent"], 2))
        self.assertEqual(match.group(4), f"{mars['leader_stability_percent']:.2f}")
        self.assertEqual(match.group(5), f"{mars['top3_stability_percent']:.2f}")
        definitions = {scenario["scenario_id"]: scenario for scenario in payload["scenario_definitions"]}
        changes = [change for change in mars["leader_changes"] if definitions[change["scenario_id"]]["family"] != "random"]
        self.assertEqual(len(changes), 4)
        craters_count = sum(change["replacement_site_id"] == "earth_craters_of_the_moon_idaho" for change in changes)
        svalbard_count = sum(change["replacement_site_id"] == "earth_svalbard_longyearbyen" for change in changes)
        self.assertIn(f"Craters of the Moon x{craters_count}, Svalbard x{svalbard_count}", paragraph)
        self.assertIn("not scientific probabilities", paragraph)
        self.assertIn("not correctness of weights or flags", paragraph)


if __name__ == "__main__":
    unittest.main()