import json
import unittest
from pathlib import Path

from PIL import Image


class TestMoonTargetImages(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[1]

    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((cls.project_root / "dashboard/target_sites.json").read_text(encoding="utf-8"))
        cls.moon = [site for site in cls.catalog["target_sites"] if site["body"] == "Moon"]

    def test_all_moon_images_are_existing_local_webp_assets(self):
        asset_root = (self.project_root / "dashboard/assets/targets").resolve()
        for site in self.moon:
            for photo in site.get("images", []):
                with self.subTest(site=site["id"], image=photo["src"]):
                    self.assertTrue(photo["src"].startswith("assets/targets/"))
                    path = (self.project_root / "dashboard" / photo["src"]).resolve()
                    self.assertTrue(path.is_relative_to(asset_root))
                    self.assertEqual(path.suffix, ".webp")
                    self.assertTrue(path.is_file())
                    with Image.open(path) as image:
                        self.assertEqual(image.format, "WEBP")
                        self.assertGreater(image.width, 0)
                        self.assertGreater(image.height, 0)
                        image.verify()

    def test_all_moon_images_have_required_attribution_fields(self):
        required = {"src", "alt", "caption", "credit", "source_url"}
        for site in self.moon:
            for photo in site.get("images", []):
                with self.subTest(site=site["id"], image=photo.get("src")):
                    self.assertTrue(required.issubset(photo))
                    self.assertTrue(set(photo).issubset(required | {"license"}))
                    for field in required:
                        self.assertIsInstance(photo[field], str)
                        self.assertTrue(photo[field].strip())
                    self.assertTrue(photo["source_url"].startswith("https://"))
                    if "license" in photo:
                        self.assertIsInstance(photo["license"], str)
                        self.assertTrue(photo["license"].strip())

    def test_all_moon_images_are_under_400_kb(self):
        for site in self.moon:
            for photo in site.get("images", []):
                with self.subTest(site=site["id"], image=photo["src"]):
                    self.assertLessEqual((self.project_root / "dashboard" / photo["src"]).stat().st_size, 400_000)

    def test_target_ids_and_moon_mappings_remain_valid(self):
        sites = self.catalog["target_sites"]
        ids = [site["id"] for site in sites]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(self.moon), 7)
        self.assertEqual(len(self.catalog["analog_matches"]["moon"]), 15)
        moon_ids = {site["id"] for site in self.moon}
        self.assertTrue(all(match["target_site_id"] in moon_ids for match in self.catalog["analog_matches"]["moon"]))


if __name__ == "__main__":
    unittest.main()