"""Detail d'une organisation."""

from __future__ import annotations

from fastapi import APIRouter

from ...schemas import OrganizationDetail
from ..deps import ClientDep

router = APIRouter(prefix="/organizations", tags=["organisations"])


@router.get("/{organization_id}", response_model=OrganizationDetail, summary="Detail d'une organisation")
async def get_organization(organization_id: str, client: ClientDep) -> OrganizationDetail:
    payload = await client.get_organization(organization_id)
    return OrganizationDetail(**payload)
