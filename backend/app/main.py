"""Point d'entree de l'API DataFrance Explorer."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from .api.routes import datasets, organizations, overview, search
from .config import get_settings
from .database import SessionLocal, init_db
from .models import Dataset, IngestionRun, Organization
from .services.catalog import CatalogError
from .services.tabular import TabularError

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare la base locale et le client HTTP reserve aux apercus de fichiers."""
    await init_db()
    http = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout, connect=10.0),
        headers={
            "User-Agent": settings.http_user_agent,
            "Accept": "*/*",
        },
        follow_redirects=True,
    )
    app.state.http = http
    try:
        yield
    finally:
        await http.aclose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Gestion d'erreurs
# --------------------------------------------------------------------------- #
@app.exception_handler(CatalogError)
async def catalog_error_handler(_: Request, exc: CatalogError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc), "source": "catalogue_local"},
    )


@app.exception_handler(TabularError)
async def tabular_error_handler(_: Request, exc: TabularError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc), "source": "traitement_local"},
    )


# --------------------------------------------------------------------------- #
# Routes techniques
# --------------------------------------------------------------------------- #
@app.get("/", include_in_schema=False)
async def root() -> dict[str, Any]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "mode": "catalogue local (ingestion data.gouv.fr)",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["technique"], summary="Etat du service et du catalogue")
async def health(deep: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "version": settings.app_version,
        "mode": "catalogue local",
        "database": settings.database_url,
    }
    started = time.perf_counter()
    try:
        async with SessionLocal() as session:
            datasets_count = int(
                await session.scalar(select(func.count()).select_from(Dataset)) or 0
            )
            organizations_count = int(
                await session.scalar(select(func.count()).select_from(Organization))
                or 0
            )
            last_run = await session.scalar(
                select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1)
            )
    except Exception as exc:  # noqa: BLE001 - l'erreur doit rester lisible
        payload.update({"status": "degraded", "database_error": str(exc)})
        return payload

    payload.update(
        {
            "datasets": datasets_count,
            "organizations": organizations_count,
            "database_latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "catalog_empty": datasets_count == 0,
        }
    )
    if last_run is not None:
        payload["last_ingestion"] = {
            "status": last_run.status,
            "started_at": last_run.started_at.isoformat()
            if last_run.started_at
            else None,
            "finished_at": last_run.finished_at.isoformat()
            if last_run.finished_at
            else None,
            "datasets_count": last_run.datasets_count,
            "organizations_count": last_run.organizations_count,
            "resources_count": last_run.resources_count,
        }
    if deep and datasets_count == 0:
        payload["hint"] = "Base vide : lancez `python -m app.ingest`."
    return payload


# --------------------------------------------------------------------------- #
# Routes metier
# --------------------------------------------------------------------------- #
app.include_router(search.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(overview.router, prefix="/api")
