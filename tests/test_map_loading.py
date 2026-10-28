import re
import unittest
from pathlib import Path


class TestMapLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).resolve().parents[1] / "dashboard/index.html").read_text(encoding="utf-8")

    def test_accessible_overlay_and_body_messages(self):
        self.assertRegex(self.html, r'id="map-loading-overlay"[^>]*role="status"[^>]*aria-live="polite"[^>]*hidden')
        for body in ("Earth", "Moon", "Mars"):
            self.assertIn(f"Loading {body} map", self.html)
        self.assertIn('id="map-loading-spinner" aria-hidden="true"', self.html)

    def test_delayed_show_warning_hard_dismiss_and_ready_cleanup(self):
        self.assertIn("const MAP_LOADING_DELAY_MS = 400;", self.html)
        self.assertIn("const MAP_LOADING_WARNING_MS = 15000;", self.html)
        self.assertIn("const MAP_LOADING_DISMISS_MS = 30000;", self.html)
        self.assertIn("Map is taking longer than expected. Check your connection.", self.html)
        self.assertIn("setTimeout(() => finishMapLoading(state), MAP_LOADING_DISMISS_MS)", self.html)
        self.assertIn("state.timers.forEach(clearTimeout);", self.html)
        self.assertIn("state.removals.forEach(remove => remove());", self.html)
        self.assertIn("if (!state || state !== mapLoadingState) return;", self.html)
        watcher = self.html.split("function watchCesiumMapLoading(viewer, state)", 1)[1].split("function setMapNotice", 1)[0]
        self.assertIn("tileLoadProgressEvent.addEventListener", watcher)
        self.assertIn("scene.postRender.addEventListener", watcher)
        self.assertIn("if (tilesReady) finishMapLoading(state);", watcher)
        self.assertNotIn("console.", watcher)

    def test_overlay_is_nonblocking_and_respects_reduced_motion(self):
        overlay_style = re.search(r"\.map-loading-overlay\s*\{([^}]+)\}", self.html)
        self.assertIsNotNone(overlay_style)
        self.assertIn("pointer-events: none", overlay_style.group(1))
        self.assertIn("calc(100% - 24px)", overlay_style.group(1))
        self.assertRegex(self.html, r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*\.map-loading-spinner\s*\{\s*animation:\s*none;")

    def test_preconnects_reuse_existing_map_hosts(self):
        for host in ("cesium.com", "trek.nasa.gov", "gibs.earthdata.nasa.gov", "tile.openstreetmap.org"):
            with self.subTest(host=host):
                self.assertIn(f'<link rel="preconnect" href="https://{host}" crossorigin>', self.html)
                self.assertIn(f"https://{host}/", self.html)


if __name__ == "__main__":
    unittest.main()