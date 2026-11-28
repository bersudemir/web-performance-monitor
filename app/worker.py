"""Run independently: python -m app.worker."""

import logging
from datetime import datetime, timezone
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.infrastructure.database import SessionLocal
from app.infrastructure.http_check import check_url
from app.infrastructure.models import CheckResult, Site

log = logging.getLogger(__name__)
REFRESH_SECONDS = 5


def check_site(site_id: int) -> None:
    try:
        with SessionLocal.begin() as session:
            site = session.get(Site, site_id, with_for_update=True)
            if site is None:
                return
            # The row lock serializes checks for this site across worker processes.
            url = site.url
            checked_at = datetime.now(timezone.utc)
            up, code, response_ms, error = check_url(url)
            session.add(CheckResult(site_id=site_id, checked_at=checked_at, is_up=up,
                                    status_code=code, response_ms=response_ms, error=error))
    except Exception:
        log.exception("Site kontrolü başarısız: %s", site_id)


class SiteWorker:
    def __init__(self, scheduler=None):
        self.scheduler = scheduler or BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1})
        self.intervals = {}

    def refresh(self) -> None:
        with SessionLocal() as session:
            sites = session.execute(select(Site.id, Site.check_interval_seconds)).all()
        desired = {site_id: seconds for site_id, seconds in sites}
        for site_id in self.intervals.keys() - desired.keys():
            self.scheduler.remove_job(f"site-{site_id}")
        for site_id, seconds in desired.items():
            if self.intervals.get(site_id) != seconds:
                self.scheduler.add_job(check_site, "interval", seconds=seconds, id=f"site-{site_id}",
                                       args=[site_id], replace_existing=True, max_instances=1,
                                       coalesce=True, next_run_time=datetime.now(timezone.utc))
        self.intervals = desired

    def run(self) -> None:
        self.scheduler.start()
        try:
            while True:
                try:
                    self.refresh()
                except Exception:
                    log.exception("Site listesi yenilenemedi")
                sleep(REFRESH_SECONDS)
        finally:
            self.scheduler.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SiteWorker().run()
