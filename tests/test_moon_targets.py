import hashlib
import json
import math
import re
import unittest
from pathlib import Path


class TestMoonReferenceRegions(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[1]
    new_ids = {"aristarchus-plateau", "cabeus-crater", "schrodinger-basin"}

    @classmethod
    def setUpClass(cls):
        cls.raw = (cls.project_root / "dashboard/target_sites.json").read_bytes().decode("utf-8")
        cls.catalog = json.loads(cls.raw)

    def test_seven_moon_regions_preserve_original_four(self):
        moon = [site for site in self.catalog["target_sites"] if site["body"] == "Moon"]
        original_ids = ["shackleton-crater", "malapert-massif", "marius-hills", "mare-tranquillitatis-apollo-11"]
        self.assertEqual(len(moon), 7)
        self.assertEqual([site["id"] for site in moon[:4]], original_ids)
        self.assertEqual({site["id"] for site in moon[4:]}, self.new_ids)
        boundary = re.search(r',\r?\n    \{\r?\n      "id": "aristarchus-plateau"', self.raw)
        self.assertIsNotNone(boundary)
        frozen = json.loads(json.dumps(self.catalog))
        image_counts = {"shackleton-crater": 2, "malapert-massif": 2, "marius-hills": 1, "mare-tranquillitatis-apollo-11": 2, "aristarchus-plateau": 0, "cabeus-crater": 1, "schrodinger-basin": 0}
        for site in frozen["target_sites"]:
            if site["body"] == "Moon":
                count = image_counts[site["id"]]
                if count:
                    site["images"] = site.get("images", [])[:count]
                else:
                    site.pop("images", None)

        def canonical(value):
            if isinstance(value, dict):
                return {key: canonical(item) for key, item in value.items()}
            if isinstance(value, list):
                return [canonical(item) for item in value]
            if isinstance(value, float) and value.is_integer():
                return int(value)
            return value

        frozen_bytes = json.dumps(canonical(frozen), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(hashlib.sha256(frozen_bytes).hexdigest(), "d291de8b7dc493fd390d33b6ab0efaa1133d2a5610aa28b48d91ab52e1d6359a")

    def test_new_regions_have_valid_required_fields_and_coordinates(self):
        sites = self.catalog["target_sites"]
        self.assertEqual(len({site["id"] for site in sites}), len(sites))
        required_strings = ("id", "name", "body", "short_description", "mission_relevance", "source_note")
        source_note = "Approximate coordinates; verify against USGS Gazetteer of Planetary Nomenclature / NASA LROC before use."
        new_sites = [site for site in sites if site["id"] in self.new_ids]
        self.assertEqual(len(new_sites), 3)
        for site in new_sites:
            with self.subTest(site=site["id"]):
                self.assertRegex(site["id"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                for field in required_strings:
                    self.assertIsInstance(site[field], str)
                    self.assertTrue(site[field].strip())
                self.assertEqual(site["body"], "Moon")
                self.assertIs(site["coords_approximate"], True)
                self.assertTrue(math.isfinite(site["lat"]))
                self.assertTrue(math.isfinite(site["lon"]))
                self.assertGreaterEqual(site["lat"], -90)
                self.assertLessEqual(site["lat"], 90)
                self.assertGreaterEqual(site["lon"], 0)
                self.assertLessEqual(site["lon"], 360)
                self.assertIsInstance(site["key_features"], list)
                self.assertTrue(site["key_features"])
                self.assertTrue(all(isinstance(feature, str) and feature.strip() for feature in site["key_features"]))
                self.assertEqual(site["source_note"], source_note)
                self.assertTrue({"status", "flags", "flags_status"}.isdisjoint(site))

    def test_analog_mappings_remain_byte_identical_and_unlinked(self):
        block = self.raw[self.raw.index('  "analog_matches":'):]
        self.assertEqual(hashlib.sha256(block.encode("utf-8")).hexdigest(), "a46232c6a516d936a3987f56788dc8647af988c3aff4ee86942b52a44c67f626")
        moon_matches = self.catalog["analog_matches"]["moon"]
        self.assertEqual(len(moon_matches), 15)
        for body_matches in self.catalog["analog_matches"].values():
            self.assertEqual(len({match["earth_analog_id"] for match in body_matches}), len(body_matches))
            self.assertTrue(all(match["target_site_id"] not in self.new_ids for match in body_matches))

    def test_new_images_exist_and_only_cabeus_reuses_existing_metadata(self):
        by_id = {site["id"]: site for site in self.catalog["target_sites"]}
        self.assertEqual(by_id["cabeus-crater"]["images"][:1], [by_id["shackleton-crater"]["images"][0]])
        for site_id in self.new_ids:
            for image in by_id[site_id].get("images", []):
                self.assertFalse(image["src"].startswith(("http:", "https:")))
                self.assertTrue((self.project_root / "dashboard" / image["src"]).is_file())
                for field in ("src", "alt", "caption", "credit", "source_url"):
                    self.assertIsInstance(image.get(field), str)
                    self.assertTrue(image[field].strip())
                self.assertTrue(image["src"].startswith("assets/targets/"))
                path = (self.project_root / "dashboard" / image["src"]).resolve()
                self.assertTrue(path.is_relative_to((self.project_root / "dashboard/assets/targets").resolve()))
                self.assertEqual(path.suffix, ".webp")
                self.assertTrue(image["source_url"].startswith("https://"))
                self.assertLessEqual(path.stat().st_size, 400_000)


if __name__ == "__main__":
    unittest.main()