import json
import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    sync_playwright = None


DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"


class QuietDashboardHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@unittest.skipIf(sync_playwright is None, "Install requirements-dev.txt to run browser regressions")
class TestDashboardSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(
            headless=True, executable_path=os.environ.get("PTAE_TEST_BROWSER")
        )
        cls.addClassCleanup(cls.browser.close)
        handler = partial(QuietDashboardHandler, directory=str(DASHBOARD_DIR))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.addClassCleanup(cls.server.server_close)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.addClassCleanup(cls.server_thread.join, timeout=5)
        cls.addClassCleanup(cls.server.shutdown)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.catalog = json.loads((DASHBOARD_DIR / "target_sites.json").read_text(encoding="utf-8"))

    def setUp(self):
        context = self.browser.new_context(viewport={"width": 1280, "height": 900})
        self.addCleanup(context.close)
        context.route(
            "**/*",
            lambda route: route.continue_() if route.request.url.startswith(self.base_url) else route.abort(),
        )
        self.page = context.new_page()
        self.page.goto(self.base_url + "legacy.html", wait_until="load")
        self.page.locator("#tab-map").click()
        expect(self.page.locator(".target-match-select").first).to_be_visible()

    def test_selecting_analog_updates_comparison_and_target(self):
        targets = {site["id"]: site for site in self.catalog["target_sites"]}
        for body in ("moon", "mars"):
            self.page.locator(f"#btn-target-{body}").click()
            for match in self.catalog["analog_matches"][body]:
                with self.subTest(body=body, analog=match["earth_analog_id"]):
                    button = self.page.locator(
                        f'.target-match-item[data-earth-analog-id="{match["earth_analog_id"]}"] button'
                    )
                    analog_name = button.inner_text().split(" · ")[0]
                    button.click()
                    target_name = targets[match["target_site_id"]]["name"]
                    expect(self.page.locator("#target-comparison-pair .target-comparison-side h3").first).to_have_text(analog_name)
                    expect(self.page.locator("#target-comparison-pair .target-side h3")).to_have_text(target_name)
                    expect(self.page.locator("#site-title")).to_have_text(target_name)

    def test_explicit_target_selection_takes_precedence(self):
        self.page.locator('.target-match-item[data-earth-analog-id="iceland"] button').click()
        self.page.locator("#tab-data").click()
        self.page.get_by_role("button", name="Shackleton Crater · Moon", exact=True).click()
        expect(self.page.locator("#target-comparison-pair .target-side h3")).to_have_text("Shackleton Crater")
        expect(self.page.locator("#site-title")).to_have_text("Shackleton Crater")


@unittest.skipIf(sync_playwright is None, "Install requirements-dev.txt to run browser regressions")
class TestMainApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(
            headless=True, executable_path=os.environ.get("PTAE_TEST_BROWSER")
        )
        cls.addClassCleanup(cls.browser.close)
        handler = partial(QuietDashboardHandler, directory=str(DASHBOARD_DIR))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.addClassCleanup(cls.server.server_close)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.addClassCleanup(cls.server_thread.join, timeout=5)
        cls.addClassCleanup(cls.server.shutdown)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.results = json.loads((DASHBOARD_DIR / "global_results.json").read_text(encoding="utf-8"))

    def setUp(self):
        context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.addCleanup(context.close)
        context.route(
            "**/*",
            lambda route: route.continue_() if route.request.url.startswith(self.base_url) else route.abort(),
        )
        self.page = context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.base_url, wait_until="load")
        expect(self.page.locator("#rows .row").first).to_be_visible()

    def test_lists_every_region_and_selecting_one_shows_evidence(self):
        expect(self.page.locator("#rows .row")).to_have_count(len(self.results["sites"]))
        self.page.locator("#rows .row").nth(1).click()
        expect(self.page.locator("#detail h2")).not_to_be_empty()
        expect(self.page.locator("#detail")).to_contain_text("Where it breaks down")
        self.assertEqual(self.errors, [])

    def test_body_and_filter_controls_change_the_ranking(self):
        self.page.locator('#body-seg [data-body="moon"]').click()
        expect(self.page.locator("#target option")).to_have_count(3)
        self.page.select_option("#show", "control")
        expect(self.page.locator("#rows .row")).to_have_count(5)
        self.assertEqual(self.errors, [])

    def test_method_page_is_reachable(self):
        self.page.locator("#nav-method").click()
        expect(self.page.locator("#view-method")).to_be_visible()
        expect(self.page.locator("#view-tool")).to_be_hidden()
        expect(self.page.locator("#ref-list li").first).to_be_visible()


if __name__ == "__main__":
    unittest.main()