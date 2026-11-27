"""Run with python -m unittest discover -s tests -v."""

import json
import re
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_existing_endpoints_are_preserved(self):
        self.assertEqual(self.client.get("/").json(), {"message": "Web Performans İzleme Sistemi çalışıyor."})
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)

    def test_pages_have_no_demo_labels_or_sidebar_note(self):
        for path in ["/dashboard", "/sites", "/sites/new"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])
                self.assertIn('lang="tr"', response.text)
                for label in ["Demo", "Örnek veri", "Arayüz önizlemesi", "sidebar-note", "universite.example.com"]:
                    self.assertNotIn(label, response.text)
                for target in ["/dashboard", "/sites", "/sites/new"]:
                    self.assertIn(f'http://testserver{target}"', response.text)

    def test_empty_lists_have_no_fabricated_results(self):
        for path in ["/dashboard", "/sites"]:
            with self.subTest(path=path):
                html = self.client.get(path).text
                self.assertIn("Henüz kayıtlı web sitesi bulunmuyor.", html)
                self.assertNotIn("UP", html)
                self.assertNotIn("DOWN", html)
                self.assertNotIn('class="http-code"', html)
                self.assertNotIn('/sites/1"', html)
        values = re.findall(r'<div class="stat-value">([^<]+)', self.client.get("/dashboard").text)
        self.assertEqual(values, ["0", "—", "—"])

    def test_unknown_sites_and_static_assets(self):
        for site_id in [1, 2, 3, 4, 999]:
            self.assertEqual(self.client.get(f"/sites/{site_id}").status_code, 404)
        self.assertEqual(self.client.get("/sites/invalid").status_code, 422)
        for path in ["/static/css/app.css", "/static/js/detail.js", "/static/js/form.js"]:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_registration_is_inactive(self):
        html = self.client.get("/sites/new").text
        self.assertIn("kayıt işlemi aktif değildir", html)
        self.assertRegex(html, r'<button[^>]+type="button"[^>]+disabled[^>]*>Siteyi Kaydet</button>')
        self.assertNotIn("form-preview", html)
        for field in ["site-name", "site-url", "site-interval"]:
            self.assertIn(f'id="{field}"', html)
        self.assertEqual(self.client.post("/sites/new", data={"name": "Test", "url": "https://example.com"}).status_code, 405)
        self.assertIn("Henüz kayıtlı web sitesi bulunmuyor.", self.client.get("/sites").text)

    def site_fixture(self, history=None):
        # Test-only input for the future data-source boundary, never used by the app.
        return {"id": 10, "name": "Test Site", "url": "https://example.com", "interval": 5,
                "up": None, "code": None, "response_ms": None, "last_check": None,
                "uptime": None, "average_ms": None, "history": history or []}

    def test_future_site_without_measurements_has_no_status_or_chart(self):
        with patch("app.presentation.pages.get_sites", return_value=[self.site_fixture()]):
            html = self.client.get("/sites/10").text
            self.assertIn("Henüz ölçüm yok", html)
            self.assertIn("Henüz kontrol kaydı bulunmuyor.", html)
            self.assertNotIn("chart-data", html)
            self.assertNotIn("chart.js@", html)
            for fabricated in ["UP", "DOWN", "%0", "None", "0 ms"]:
                self.assertNotIn(fabricated, html)
            listing = self.client.get("/sites").text
            self.assertIn("Henüz ölçüm yok", listing)
            self.assertNotIn("DOWN", listing)
            dashboard = self.client.get("/dashboard").text
            self.assertEqual(re.findall(r'<div class="stat-value">([^<]+)', dashboard), ["1", "—", "—"])

    def test_future_chart_uses_only_supplied_measurements(self):
        history = [
            {"time": "27.11.2026 14:05", "up": False, "code": None, "response_ms": None},
            {"time": "27.11.2026 14:00", "up": True, "code": 200, "response_ms": 0},
        ]
        site = self.site_fixture(history)
        site.update(up=False, uptime=50, average_ms=0)
        with patch("app.presentation.pages.get_sites", return_value=[site]):
            response = self.client.get("/sites/10")
        self.assertEqual(response.status_code, 200)
        chart = json.loads(re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', response.text).group(1))
        self.assertEqual(chart, {"labels": ["27.11.2026 14:00"], "values": [0]})
        self.assertIn("%50", response.text)
        self.assertNotIn("None", response.text)


if __name__ == "__main__":
    unittest.main()
