"""Minimal HTML routes; demo data stays in the presentation layer."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.presentation.demo import demo_sites


PRESENTATION_DIR = Path(__file__).resolve().parent
STATIC_DIR = PRESENTATION_DIR / "static"
templates = Jinja2Templates(directory=str(PRESENTATION_DIR / "templates"))
router = APIRouter(include_in_schema=False)


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request):
    sites = demo_sites()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "active": "dashboard", "sites": sites, "up_count": sum(site["up"] for site in sites),
    })


@router.get("/sites", response_class=HTMLResponse, name="site_list")
def site_list(request: Request):
    return templates.TemplateResponse(request=request, name="sites.html", context={
        "active": "sites", "sites": demo_sites(),
    })


@router.get("/sites/new", response_class=HTMLResponse, name="site_new")
def site_new(request: Request):
    return templates.TemplateResponse(request=request, name="site_new.html", context={"active": "new"})


@router.get("/sites/{site_id}", response_class=HTMLResponse, name="site_detail")
def site_detail(request: Request, site_id: int):
    site = next((item for item in demo_sites() if item["id"] == site_id), None)
    if site is None:
        raise HTTPException(status_code=404, detail="Site bulunamadı.")
    chart = {
        "labels": [check["time"] for check in reversed(site["history"])],
        "values": [check["response_ms"] for check in reversed(site["history"])],
    }
    return templates.TemplateResponse(request=request, name="site_detail.html", context={
        "active": "sites", "site": site, "chart": chart,
    })
