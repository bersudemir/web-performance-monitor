"""HTML routes for site management and performance views."""
from pathlib import Path
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.sites import SiteService, display_site
from app.infrastructure.database import SessionLocal

PRESENTATION_DIR = Path(__file__).resolve().parent
STATIC_DIR = PRESENTATION_DIR / "static"
templates = Jinja2Templates(directory=str(PRESENTATION_DIR / "templates"))
router = APIRouter(include_in_schema=False)


def get_session():
    with SessionLocal() as session:
        yield session


def get_sites(session: Session):
    return [display_site(site) for site in SiteService(session).list()]


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request, session: Session = Depends(get_session)):
    sites = get_sites(session)
    measured = [site for site in sites if site["up"] is not None]
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "active": "dashboard", "sites": sites,
        "up_count": sum(site["up"] is True for site in measured) if measured else None,
        "down_count": sum(site["up"] is False for site in measured) if measured else None,
    })


@router.get("/sites", response_class=HTMLResponse, name="site_list")
def site_list(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request=request, name="sites.html", context={
        "active": "sites", "sites": get_sites(session),
    })


def form_page(request: Request, site=None, error=None, status_code=200):
    return templates.TemplateResponse(request=request, name="site_new.html", status_code=status_code,
                                      context={"active": "new", "site": site, "error": error})


@router.get("/sites/new", response_class=HTMLResponse, name="site_new")
def site_new(request: Request):
    return form_page(request)


@router.post("/sites/new", name="site_create")
def site_create(request: Request, name: str = Form(), url: str = Form(), interval: int = Form(),
                session: Session = Depends(get_session)):
    try:
        site = SiteService(session).create(name, url, interval)
    except ValueError as error:
        return form_page(request, {"name": name, "url": url, "interval": interval}, str(error), 422)
    return RedirectResponse(request.url_for("site_detail", site_id=site.id), status_code=303)


def find_site(session: Session, site_id: int):
    site = SiteService(session).get(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site bulunamadı.")
    return site


@router.get("/sites/{site_id}", response_class=HTMLResponse, name="site_detail")
def site_detail(request: Request, site_id: int, session: Session = Depends(get_session)):
    site = display_site(find_site(session, site_id))
    measured = [check for check in reversed(site["history"]) if check["response_ms"] is not None]
    chart = {"labels": [check["time"] for check in measured],
             "values": [check["response_ms"] for check in measured]}
    return templates.TemplateResponse(request=request, name="site_detail.html", context={
        "active": "sites", "site": site, "chart": chart,
    })


@router.get("/sites/{site_id}/edit", response_class=HTMLResponse, name="site_edit")
def site_edit(request: Request, site_id: int, session: Session = Depends(get_session)):
    return form_page(request, display_site(find_site(session, site_id)))


@router.post("/sites/{site_id}/edit", name="site_update")
def site_update(request: Request, site_id: int, name: str = Form(), url: str = Form(),
                interval: int = Form(), session: Session = Depends(get_session)):
    site = find_site(session, site_id)
    try:
        SiteService(session).update(site, name, url, interval)
    except ValueError as error:
        return form_page(request, {"id": site_id, "name": name, "url": url, "interval": interval}, str(error), 422)
    return RedirectResponse(request.url_for("site_detail", site_id=site_id), status_code=303)


@router.post("/sites/{site_id}/delete", name="site_delete")
def site_delete(request: Request, site_id: int, session: Session = Depends(get_session)):
    SiteService(session).delete(find_site(session, site_id))
    return RedirectResponse(request.url_for("site_list"), status_code=303)
