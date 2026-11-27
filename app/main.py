from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.presentation.pages import STATIC_DIR, router as pages_router

app = FastAPI(
    title="Web Performans İzleme Sistemi",
    version="0.1.0"
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(pages_router)


@app.get("/")
def home():
    return {
        "message": "Web Performans İzleme Sistemi çalışıyor."
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }
