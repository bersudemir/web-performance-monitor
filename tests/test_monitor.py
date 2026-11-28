"""Network policy, scheduler reconciliation and persisted check results."""

import socket
import unittest
from unittest.mock import MagicMock, patch

import httpx
from sqlalchemy import delete

from app.application.sites import display_site
from app.infrastructure.database import SessionLocal
from app.infrastructure.http_check import PinnedBackend, UnsafeAddress, check_url, public_addresses
from app.infrastructure.models import CheckResult, Site
from app.worker import SiteWorker, check_site


class MonitorTests(unittest.TestCase):
    def test_private_dns_and_mixed_dns_are_blocked(self):
        for addresses in (("127.0.0.1",), ("8.8.8.8", "192.168.1.2"), ("fe80::1",)):
            records = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 80)) for address in addresses]
            with self.subTest(addresses=addresses), patch("socket.getaddrinfo", return_value=records):
                with self.assertRaises(UnsafeAddress):
                    public_addresses("example.com", 80)
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 80))]):
            self.assertEqual(public_addresses("example.com", 80), ["8.8.8.8"])
            with patch("httpcore._backends.sync.SyncBackend.connect_tcp") as dial:
                PinnedBackend().connect_tcp("example.com", 80)
                self.assertEqual(dial.call_args.args[:2], ("8.8.8.8", 80))

    def test_status_redirect_and_timeout(self):
        with patch("httpx.Client.stream") as stream:
            stream.return_value.__enter__.return_value = httpx.Response(
                302, headers={"location": "http://127.0.0.1/private"})
            self.assertEqual(check_url("https://example.com/redirect")[:3], (False, None, None))
        self.assertFalse(check_url("file:///etc/passwd")[0])
        with patch("httpx.Client.stream") as stream:
            stream.return_value.__enter__.return_value = httpx.Response(503)
            self.assertEqual(check_url("https://example.com")[:2], (False, 503))
            stream.return_value.__enter__.side_effect = httpx.TimeoutException("timed out")
            self.assertEqual(check_url("https://example.com")[:3], (False, None, None))

    def test_worker_persists_failure_and_statistics(self):
        with SessionLocal.begin() as session:
            site = Site(name="Worker test", url="https://example.com", check_interval_seconds=60)
            session.add(site)
            session.flush()
            site_id = site.id
        try:
            with patch("app.worker.check_url", return_value=(False, None, None, "timeout")):
                check_site(site_id)
            with SessionLocal() as session:
                site = session.get(Site, site_id)
                result = site.check_results[0]
                self.assertFalse(result.is_up)
                self.assertEqual(result.error, "timeout")
                self.assertIsNone(result.response_ms)
                view = display_site(site)
                self.assertEqual(view["uptime"], 0)
                self.assertIsNone(view["average_ms"])
                self.assertIsNone(view["p95_ms"])
        finally:
            with SessionLocal.begin() as session:
                session.execute(delete(Site).where(Site.id == site_id))

    def test_response_statistics_use_measured_values_only(self):
        with SessionLocal.begin() as session:
            site = Site(name="Statistics test", url="https://example.com", check_interval_seconds=60)
            session.add(site)
            session.flush()
            site_id = site.id
            for up, response_ms in ((True, 0), (True, 100), (False, 400), (False, None)):
                session.add(CheckResult(site_id=site_id, is_up=up, response_ms=response_ms))
        try:
            with SessionLocal() as session:
                view = display_site(session.get(Site, site_id))
                self.assertEqual(view["uptime"], 50.0)
                self.assertEqual(view["average_ms"], 167)
                self.assertEqual(view["min_ms"], 0)
                self.assertEqual(view["max_ms"], 400)
                self.assertEqual(view["p95_ms"], 400)
        finally:
            with SessionLocal.begin() as session:
                session.execute(delete(Site).where(Site.id == site_id))

    def test_refresh_detects_add_update_delete(self):
        scheduler = MagicMock()
        worker = SiteWorker(scheduler)
        with SessionLocal.begin() as session:
            site = Site(name="Schedule test", url="https://example.com", check_interval_seconds=60)
            session.add(site)
            session.flush()
            site_id = site.id
        try:
            worker.refresh()
            self.assertEqual(worker.intervals[site_id], 60)
            with SessionLocal.begin() as session:
                session.get(Site, site_id).check_interval_seconds = 120
            worker.refresh()
            self.assertEqual(worker.intervals[site_id], 120)
        finally:
            with SessionLocal.begin() as session:
                session.execute(delete(Site).where(Site.id == site_id))
        worker.refresh()
        scheduler.remove_job.assert_any_call(f"site-{site_id}")
