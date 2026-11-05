"""Point d'entree de l'API DataFrance Explorer."""

from __future__ import annotations

import asyncio
import contextlib
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import datasets, organizations, overview, search
from .config import get_settings
from .services.datagouv import DataGouvClient, DataGouvError
from .services.tabular import TabularError

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cree un client HTTP unique (pool de connexions) pour toute la duree de vie."""
    http = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout, connect=10.0),
        headers={
            "User-Agent": settings.http_user_agent,
            "Accept": "application/json",
        },
        follow_redirects=True,
    )
    app.state.http = http
    app.state.datagouv = DataGouvClient(settings, http)
    # Precharge le catalogue d'organisations sans bloquer le demarrage.
    warmup = asyncio.create_task(app.state.datagouv.warm_organization_catalog())
    try:
        yield
    finally:
        warmup.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await warmup
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
@app.exception_handler(DataGouvError)
async def datagouv_error_handler(_: Request, exc: DataGouvError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc), "source": "data.gouv.fr"},
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
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["technique"], summary="Etat du service")
async def health(deep: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "version": settings.app_version,
        "upstream": settings.datagouv_api_base,
    }
    if deep:
        started = time.perf_counter()
        try:
            client: DataGouvClient = app.state.datagouv
            await client.search_datasets(page=1, page_size=1)
        except DataGouvError as exc:
            payload.update({"status": "degraded", "upstream_error": str(exc)})
        else:
            payload["upstream_latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return payload


# --------------------------------------------------------------------------- #
# Routes metier
# --------------------------------------------------------------------------- #
app.include_router(search.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(overview.router, prefix="/api")
