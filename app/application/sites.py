"""Site operations and display data."""

from datetime import datetime
from math import ceil
from ipaddress import ip_address
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.models import Site

ISTANBUL = ZoneInfo("Europe/Istanbul")


def validate_site(name: str, url: str, interval: int) -> tuple[str, str, int]:
    name, url = name.strip(), url.strip()
    try:
        parsed = urlsplit(url)
        valid_host = bool(parsed.hostname) and parsed.port != 0
        host = parsed.hostname or ""
        try:
            valid_host = valid_host and ip_address(host).is_global
        except ValueError:
            valid_host = valid_host and host.lower() != "localhost" and not host.lower().endswith(".local")
    except ValueError:
        valid_host = False
    if not name or len(name) > 120:
        raise ValueError("Site adı 1–120 karakter olmalıdır.")
    if (len(url) > 2048 or parsed.scheme.lower() not in {"http", "https"}
            or not valid_host or parsed.username or parsed.password or any(c.isspace() for c in url)):
        raise ValueError("Geçerli bir http:// veya https:// URL'si girin.")
    if interval not in {1, 5, 10, 15, 30, 60}:
        raise ValueError("Geçerli bir kontrol aralığı seçin.")
    return name, url, interval * 60


class SiteService:
    def __init__(self, session: Session):
        self.session = session

    def list(self) -> list[Site]:
        return list(self.session.scalars(select(Site).options(selectinload(Site.check_results)).order_by(Site.id)))

    def get(self, site_id: int) -> Site | None:
        return self.session.scalar(select(Site).options(selectinload(Site.check_results)).where(Site.id == site_id))

    def create(self, name: str, url: str, interval: int) -> Site:
        name, url, seconds = validate_site(name, url, interval)
        site = Site(name=name, url=url, check_interval_seconds=seconds)
        self.session.add(site)
        self.session.commit()
        self.session.refresh(site)
        return site

    def update(self, site: Site, name: str, url: str, interval: int) -> None:
        site.name, site.url, site.check_interval_seconds = validate_site(name, url, interval)
        self.session.commit()

    def delete(self, site: Site) -> None:
        self.session.delete(site)
        self.session.commit()


def display_site(site: Site) -> dict:
    checks = sorted(site.check_results, key=lambda item: (item.checked_at, item.id), reverse=True)
    latest = checks[0] if checks else None
    measured = [item.response_ms for item in checks if item.response_ms is not None]
    ordered = sorted(measured)

    def local_time(value: datetime) -> str:
        return value.astimezone(ISTANBUL).strftime("%d.%m.%Y %H:%M")

    return {
        "id": site.id, "name": site.name, "url": site.url,
        "interval": site.check_interval_seconds // 60,
        "up": latest.is_up if latest else None,
        "code": latest.status_code if latest else None,
        "error": latest.error if latest else None,
        "response_ms": latest.response_ms if latest else None,
        "last_check": local_time(latest.checked_at) if latest else None,
        "uptime": round(100 * sum(item.is_up for item in checks) / len(checks), 1) if checks else None,
        "average_ms": round(sum(measured) / len(measured)) if measured else None,
        "min_ms": ordered[0] if ordered else None,
        "max_ms": ordered[-1] if ordered else None,
        "p95_ms": ordered[ceil(0.95 * len(ordered)) - 1] if ordered else None,
        "history": [{"time": local_time(item.checked_at), "up": item.is_up,
                     "code": item.status_code, "response_ms": item.response_ms,
                     "error": item.error} for item in checks],
    }
