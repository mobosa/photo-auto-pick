"""FastAPI application entry point — serves API + frontend static files."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.upload import router as upload_router
from app.api.tasks import router as tasks_router
from app.api.results import router as results_router
from app.api.system import router as system_router
from app.models.database import init_db
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PhotoAutoPick", version="1.0.0", lifespan=lifespan)

# Register API routes
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(tasks_router, prefix="/api", tags=["tasks"])
app.include_router(results_router, prefix="/api", tags=["results"])
app.include_router(system_router, prefix="/api", tags=["system"])


# Mount static assets (JS/CSS/images from Vite build)
static_dir = settings.static_dir
assets_dir = static_dir / "assets"

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/")
async def root():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"name": "PhotoAutoPick", "version": "1.0.0", "status": "running"}


# Catch-all: serve index.html for SPA client-side routing
@app.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str):
    # Try serving exact file first
    file_path = static_dir / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))
    # Fallback to index.html for SPA routes
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"error": "Frontend not built. Run: cd frontend && npm run build"}
