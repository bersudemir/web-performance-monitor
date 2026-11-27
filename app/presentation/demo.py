"""Presentation-only fixtures. No network checks or persistence occur here."""

from datetime import datetime, timedelta


DEMO_TIME = datetime(2026, 11, 27, 14, 30)


def demo_sites():
    """Return fresh, deterministic examples so requests cannot mutate fixtures."""
    definitions = [
        (1, "Üniversite Portalı", "https://universite.example.com", 200, 184, 5),
        (2, "Kütüphane", "https://kutuphane.example.com", 200, 246, 10),
        (3, "Öğrenci Bilgi Sistemi", "https://obs.example.com", 503, 1240, 5),
        (4, "Araştırma Merkezi", "https://arastirma.example.com", 200, 312, 15),
    ]
    sites = []
    for site_id, name, url, code, response_ms, interval in definitions:
        history = []
        for index in range(12):
            check_code = code if index == 0 else (503 if site_id == 3 and index == 1 else 200)
            history.append({
                "time": (DEMO_TIME - timedelta(minutes=index * interval)).strftime("%d.%m.%Y %H:%M"),
                "code": check_code, "up": check_code == 200,
                "response_ms": response_ms if index == 0 else 150 + (site_id * 43 + index * 29) % 240,
            })
        sites.append({
            "id": site_id, "name": name, "url": url, "interval": interval,
            "code": code, "up": code == 200, "response_ms": response_ms,
            "last_check": history[0]["time"], "history": history,
            "uptime": round(sum(check["up"] for check in history) / len(history) * 100, 1),
            "average_ms": round(sum(check["response_ms"] for check in history) / len(history)),
        })
    return sites
