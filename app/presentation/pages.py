"""HTML routes awaiting a real site data source."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

PRESENTATION_DIR = Path(__file__).resolve().parent
STATIC_DIR = PRESENTATION_DIR / "static"
templates = Jinja2Templates(directory=str(PRESENTATION_DIR / "templates"))
router = APIRouter(include_in_schema=False)


def get_sites():
    """No persistence is connected yet. Replace with an application query later."""
    return []


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request):
    sites = get_sites()
    measured_sites = [site for site in sites if site["up"] is not None]
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "active": "dashboard", "sites": sites,
        "up_count": sum(site["up"] is True for site in measured_sites) if measured_sites else None,
        "down_count": sum(site["up"] is False for site in measured_sites) if measured_sites else None,
    })


@router.get("/sites", response_class=HTMLResponse, name="site_list")
def site_list(request: Request):
    return templates.TemplateResponse(request=request, name="sites.html", context={
        "active": "sites", "sites": get_sites(),
    })


@router.get("/sites/new", response_class=HTMLResponse, name="site_new")
def site_new(request: Request):
    return templates.TemplateResponse(request=request, name="site_new.html", context={"active": "new"})


@router.get("/sites/{site_id}", response_class=HTMLResponse, name="site_detail")
def site_detail(request: Request, site_id: int):
    site = next((item for item in get_sites() if item["id"] == site_id), None)
    if site is None:
        raise HTTPException(status_code=404, detail="Site bulunamadı.")
    measured_checks = [check for check in reversed(site["history"]) if check["response_ms"] is not None]
    chart = {"labels": [check["time"] for check in measured_checks],
             "values": [check["response_ms"] for check in measured_checks]}
    return templates.TemplateResponse(request=request, name="site_detail.html", context={
        "active": "sites", "site": site, "chart": chart,
    })
