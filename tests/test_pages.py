"""HTTP tests against the configured PostgreSQL database."""

from html import unescape
import re
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.main import app
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import CheckResult, Site


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.created = []

    def tearDown(self):
        with SessionLocal.begin() as session:
            for site_id in self.created:
                session.execute(delete(Site).where(Site.id == site_id))

    def create(self):
        response = self.client.post('/sites/new', data={
            'name': 'Test Portalı', 'url': 'https://example.com', 'interval': '5'}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        site_id = int(response.headers['location'].rsplit('/', 1)[-1])
        self.created.append(site_id)
        return site_id

    def test_existing_endpoints_and_static_assets(self):
        self.assertEqual(self.client.get('/health').json(), {'status': 'ok'})
        self.assertEqual(self.client.get('/docs').status_code, 200)
        self.assertEqual(self.client.get('/static/css/app.css').status_code, 200)

    def test_create_list_dashboard_detail_update_delete(self):
        site_id = self.create()
        with SessionLocal() as session:
            self.assertEqual(session.get(Site, site_id).check_interval_seconds, 300)
        for path in ('/sites', '/dashboard', f'/sites/{site_id}'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('Test Portalı', response.text)
            self.assertIn('Henüz ölçüm yok', response.text)
            if path == f'/sites/{site_id}':
                self.assertNotIn('UP · Erişilebilir', response.text)
        detail = self.client.get(f'/sites/{site_id}').text
        self.assertNotIn('chart-data', detail)
        self.assertIn('Henüz kontrol kaydı bulunmuyor.', detail)
        self.assertEqual(self.client.get(f'/sites/{site_id}/edit').status_code, 200)
        response = self.client.post(f'/sites/{site_id}/edit', data={
            'name': 'Yeni Ad', 'url': 'http://example.org/path', 'interval': '10'}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn('Yeni Ad', self.client.get(f'/sites/{site_id}').text)
        with SessionLocal() as session:
            self.assertEqual(session.get(Site, site_id).check_interval_seconds, 600)
        response = self.client.post(f'/sites/{site_id}/delete', follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.get(f'/sites/{site_id}').status_code, 404)

    def test_invalid_inputs_do_not_write(self):
        for url in ('ftp://example.com', 'https://', 'https://user:pass@example.com', 'https://example.com:invalid'):
            with self.subTest(url=url):
                response = self.client.post('/sites/new', data={
                    'name': 'Test', 'url': url, 'interval': '5'})
                self.assertEqual(response.status_code, 422)
                self.assertIn('role="alert"', response.text)
        response = self.client.post('/sites/new', data={
            'name': 'Test', 'url': 'https://example.com', 'interval': '99'})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get('/sites/999999999').status_code, 404)

    def test_malformed_url_returns_422_for_create_and_update(self):
        malformed = 'http://['
        response = self.client.post('/sites/new', data={
            'name': 'Test', 'url': malformed, 'interval': '5'})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Geçerli bir http:// veya https:// URL'si girin.", unescape(response.text))

        site_id = self.create()
        response = self.client.post(f'/sites/{site_id}/edit', data={
            'name': 'Test', 'url': malformed, 'interval': '5'})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Geçerli bir http:// veya https:// URL'si girin.", unescape(response.text))
        with SessionLocal() as session:
            self.assertEqual(session.get(Site, site_id).url, 'https://example.com')

    def test_real_results_are_displayed_and_deleted_with_site(self):
        site_id = self.create()
        with SessionLocal.begin() as session:
            session.add(CheckResult(site_id=site_id, is_up=True, status_code=200, response_ms=0))
        detail = self.client.get(f'/sites/{site_id}').text
        self.assertIn('UP · Erişilebilir', detail)
        self.assertIn('HTTP 200', detail)
        self.assertIn('chart-data', detail)
        self.assertIn('"values": [0]', detail)
        dashboard = self.client.get('/dashboard').text
        self.assertIn('UP · Erişilebilir', dashboard)
        self.assertIn('Son kontrolü başarılı olan siteler', dashboard)
        self.client.post(f'/sites/{site_id}/delete')
        with SessionLocal() as session:
            self.assertIsNone(session.get(Site, site_id))

    def test_form_and_common_text(self):
        page = self.client.get('/sites/new').text
        self.assertIn('İzlemek istediğiniz web sitesini ekleyin.', page)
        self.assertIn('Otomatik İzleme', page)
        self.assertIn('Sistem, web sitesini seçtiğiniz aralıklarla otomatik kontrol eder.', page)
        self.assertIn('AWS EC2 · Docker · PostgreSQL', page)
        self.assertNotIn('Henüz otomatik kontrol ve performans ölçümü yapılmaz.', page)
        site_id = self.create()
        self.assertIn('İzlenen web sitesinin bilgilerini güncelleyin.',
                      self.client.get(f'/sites/{site_id}/edit').text)

    def test_unmeasured_dashboard_and_connection_error_are_distinct(self):
        with patch('app.presentation.pages.get_sites', return_value=[]):
            empty = self.client.get('/dashboard').text
        self.assertIn('Erişilebilen Site', empty)
        self.assertIn('Erişilemeyen Site', empty)
        self.assertEqual(empty.count('Henüz ölçüm yok'), 2)

        site_id = self.create()
        detail = self.client.get(f'/sites/{site_id}').text
        self.assertIn('Henüz ölçüm yok', detail)
        self.assertNotIn('Bağlantı hatası', detail)
        with SessionLocal.begin() as session:
            session.add(CheckResult(site_id=site_id, is_up=False,
                                    error='<script>alert("x")</script>'))
        detail = self.client.get(f'/sites/{site_id}').text
        self.assertIn('Bağlantı hatası', detail)
        self.assertIn('DOWN · Erişilemedi', detail)
        self.assertIn('Başarılı Kontrol Oranı', detail)
        self.assertIn('&lt;script&gt;', detail)
        self.assertNotIn('<script>alert("x")</script>', detail)
        dashboard = self.client.get('/dashboard').text
        self.assertIn('Son kontrolü başarısız olan siteler', dashboard)


if __name__ == '__main__':
    unittest.main()
