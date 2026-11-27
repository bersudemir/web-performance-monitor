"""Run with python -m unittest discover -s tests -v."""

import json
import re
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.presentation.demo import demo_sites


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_existing_endpoints_are_preserved(self):
        self.assertEqual(self.client.get("/").json(), {"message": "Web Performans İzleme Sistemi çalışıyor."})
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)

    def test_all_pages_render_with_demo_disclosure(self):
        for path in ["/dashboard", "/sites", "/sites/new", *[f"/sites/{i}" for i in range(1, 5)]]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])
                self.assertIn('lang="tr"', response.text)
                self.assertIn("Örnek veri", response.text)

    def test_dashboard_counts_and_detail_links(self):
        response = self.client.get("/dashboard")
        values = re.findall(r'<div class="stat-value">(\d+)', response.text)
        self.assertEqual(values, ["4", "3", "1"])
        for site in demo_sites():
            self.assertIn(f'/sites/{site["id"]}', response.text)

    def test_metrics_and_chart_match_history(self):
        for site in demo_sites():
            with self.subTest(site=site["id"]):
                response = self.client.get(f'/sites/{site["id"]}')
                chart = json.loads(re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', response.text).group(1))
                self.assertEqual(chart["values"], [row["response_ms"] for row in reversed(site["history"])])
                self.assertEqual(chart["labels"], [row["time"] for row in reversed(site["history"])])
                self.assertEqual(site["uptime"], round(sum(row["up"] for row in site["history"]) / 12 * 100, 1))
                self.assertEqual(site["average_ms"], round(sum(row["response_ms"] for row in site["history"]) / 12))
                self.assertIn(f'>{site["average_ms"]}<', response.text)
                self.assertEqual(response.text.count('<td class="tabular">'), 24)

    def test_unknown_sites_and_static_assets(self):
        self.assertEqual(self.client.get("/sites/999").status_code, 404)
        self.assertEqual(self.client.get("/sites/invalid").status_code, 422)
        for path in ["/static/css/app.css", "/static/js/detail.js", "/static/js/form.js"]:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_form_is_preview_only(self):
        response = self.client.get("/sites/new")
        self.assertIn("bilgiler kaydedilmez", response.text)
        self.assertIn("Bilgileri Önizle", response.text)
        self.assertEqual(self.client.post("/sites/new", data={"name": "Test", "url": "https://example.com"}).status_code, 405)
        self.assertEqual(len(demo_sites()), 4)


if __name__ == "__main__":
    unittest.main()
