"""Statistiques globales sur data.gouv.fr."""

from __future__ import annotations

from fastapi import APIRouter

from ...schemas import OverviewResponse
from ..deps import ClientDep

router = APIRouter(prefix="/stats", tags=["statistiques"])


@router.get("/overview", response_model=OverviewResponse, summary="Vue d'ensemble de data.gouv.fr")
async def overview(client: ClientDep) -> OverviewResponse:
    payload = await client.get_overview()
    return OverviewResponse(**payload)
