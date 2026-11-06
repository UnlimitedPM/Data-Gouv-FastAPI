"""Dependances FastAPI partagees."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import session_dependency
from ..services.catalog import CatalogService


def get_catalog(
    session: Annotated[AsyncSession, Depends(session_dependency)],
) -> CatalogService:
    """Service de lecture du catalogue local pour la requete courante."""
    return CatalogService(session)


def get_http(request: Request) -> httpx.AsyncClient:
    """Client HTTP utilise uniquement pour telecharger les fichiers a previsualiser."""
    return request.app.state.http


CatalogDep = Annotated[CatalogService, Depends(get_catalog)]
HttpDep = Annotated[httpx.AsyncClient, Depends(get_http)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
