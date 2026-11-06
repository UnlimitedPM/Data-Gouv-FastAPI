"""Detail d'un jeu de donnees, apercu et profil des ressources."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ...schemas import (
    DatasetDetail,
    GeoResponse,
    PreviewResponse,
    ProfileResponse,
    Resource,
)
from ...services.catalog import CatalogError
from ...services.tabular import (
    TabularError,
    build_geojson,
    build_preview,
    build_profile,
)
from ..deps import CatalogDep, HttpDep, SettingsDep

router = APIRouter(prefix="/datasets", tags=["jeux de donnees"])


def _pick_resource(dataset: DatasetDetail, resource_id: str | None) -> Resource:
    resources = dataset.resources
    if not resources:
        raise CatalogError("Ce jeu de donnees ne contient aucune ressource.", status_code=404)

    if resource_id:
        for resource in resources:
            if resource.id == resource_id:
                return resource
        raise CatalogError(
            "Cette ressource n'appartient pas a ce jeu de donnees.", status_code=404
        )

    tabular = [resource for resource in resources if resource.is_tabular]
    if not tabular:
        raise TabularError(
            "Aucune ressource tabulaire (CSV, JSON, Excel, Parquet) dans ce jeu de donnees."
        )

    main = [resource for resource in tabular if resource.type == "main"]
    return (main or tabular)[0]


@router.get("/{dataset_id}", response_model=DatasetDetail, summary="Detail d'un jeu de donnees")
async def get_dataset(dataset_id: str, catalog: CatalogDep) -> DatasetDetail:
    return DatasetDetail(**await catalog.get_dataset(dataset_id))


@router.get(
    "/{dataset_id}/preview",
    response_model=PreviewResponse,
    summary="Apercu des premieres lignes d'une ressource tabulaire",
)
async def preview_dataset(
    dataset_id: str,
    catalog: CatalogDep,
    http: HttpDep,
    settings: SettingsDep,
    resource_id: str | None = Query(None, description="Identifiant de la ressource"),
    limit: int = Query(200, ge=1, le=5_000, description="Nombre de lignes a renvoyer"),
) -> PreviewResponse:
    bundle = DatasetDetail(**await catalog.get_dataset(dataset_id))
    resource = _pick_resource(bundle, resource_id)
    return await build_preview(http, settings, resource, bundle.id, limit)


@router.get(
    "/{dataset_id}/profile",
    response_model=ProfileResponse,
    summary="Profil statistique des colonnes d'une ressource tabulaire",
)
async def profile_dataset(
    dataset_id: str,
    catalog: CatalogDep,
    http: HttpDep,
    settings: SettingsDep,
    resource_id: str | None = Query(None, description="Identifiant de la ressource"),
    limit: int = Query(20_000, ge=100, le=50_000, description="Lignes analysees"),
) -> ProfileResponse:
    bundle = DatasetDetail(**await catalog.get_dataset(dataset_id))
    resource = _pick_resource(bundle, resource_id)
    return await build_profile(http, settings, resource, bundle.id, limit)


@router.get(
    "/{dataset_id}/geo",
    response_model=GeoResponse,
    summary="FeatureCollection GeoJSON pour une carte choroplethe",
)
async def geo_dataset(
    dataset_id: str,
    catalog: CatalogDep,
    http: HttpDep,
    settings: SettingsDep,
    resource_id: str | None = Query(None, description="Identifiant de la ressource GeoJSON"),
    limit: int = Query(800, ge=10, le=2_000, description="Nombre de geometries"),
) -> GeoResponse:
    bundle = DatasetDetail(**await catalog.get_dataset(dataset_id))
    resource = _pick_resource(bundle, resource_id)

    # Si la ressource choisie n'est pas GeoJSON, chercher une ressource geo.
    if (resource.format or "").lower() not in {"geojson", "json"}:
        geo_resources = [
            candidate
            for candidate in bundle.resources
            if (candidate.format or "").lower() in {"geojson", "json"}
        ]
        if geo_resources:
            resource = geo_resources[0]

    return await build_geojson(http, settings, resource, bundle.id, limit)
