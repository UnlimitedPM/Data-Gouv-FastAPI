"""Statistiques globales du catalogue local."""

from __future__ import annotations

from fastapi import APIRouter

from ...schemas import OverviewResponse
from ..deps import CatalogDep

router = APIRouter(prefix="/stats", tags=["statistiques"])


@router.get("/overview", response_model=OverviewResponse, summary="Vue d'ensemble du catalogue")
async def overview(catalog: CatalogDep) -> OverviewResponse:
    payload = await catalog.get_overview()
    return OverviewResponse(**payload)
