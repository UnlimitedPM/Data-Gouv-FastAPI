"""Recherche de jeux de donnees et d'organisations."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ...schemas import DatasetSearchResponse, OrganizationSearchResponse
from ..deps import ClientDep

router = APIRouter(prefix="/search", tags=["recherche"])


@router.get(
    "/datasets",
    response_model=DatasetSearchResponse,
    summary="Rechercher des jeux de donnees",
)
async def search_datasets(
    client: ClientDep,
    q: str | None = Query(None, description="Termes de recherche"),
    page: int = Query(1, ge=1, description="Numero de page"),
    page_size: int = Query(20, ge=1, le=100, description="Resultats par page"),
    sort: str | None = Query(
        None,
        description="Tri : -created, -last_update, -views, -followers, -reuses",
    ),
    organization: str | None = Query(None, description="Identifiant d'organisation"),
    tag: str | None = Query(None, description="Mot-cle / tag"),
    license: str | None = Query(None, description="Identifiant de licence"),
    format: str | None = Query(None, description="Format de fichier (csv, json...)"),
    format_family: str | None = Query(
        None, description="Famille de formats (tabular, geographical...)"
    ),
    producer_type: str | None = Query(
        None, description="Type de producteur (public-service, company...)"
    ),
    geozone: str | None = Query(None, description="Zone geographique"),
    granularity: str | None = Query(None, description="Granularite territoriale"),
) -> DatasetSearchResponse:
    payload = await client.search_datasets(
        query=q,
        page=page,
        page_size=page_size,
        sort=sort,
        organization=organization,
        tag=tag,
        license=license,
        format=format,
        format_family=format_family,
        producer_type=producer_type,
        geozone=geozone,
        granularity=granularity,
    )
    return DatasetSearchResponse(**payload)


@router.get(
    "/organizations",
    response_model=OrganizationSearchResponse,
    summary="Rechercher des organisations",
)
async def search_organizations(
    client: ClientDep,
    q: str | None = Query(None, description="Termes de recherche"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="Tri : -datasets, -created, -views"),
) -> OrganizationSearchResponse:
    payload = await client.search_organizations(
        query=q, page=page, page_size=page_size, sort=sort
    )
    return OrganizationSearchResponse(**payload)
