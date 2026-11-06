"""Acces au catalogue local (les requetes ne touchent plus l'API data.gouv)."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import (
    Dataset,
    DatasetFormat,
    DatasetTag,
    Organization,
    Resource,
    SiteStat,
)
from ..utils import normalize_text


class CatalogError(RuntimeError):
    """Erreur de lecture du catalogue local."""

    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


def _org_ref(organization: Organization | None) -> dict[str, Any] | None:
    if organization is None:
        return None
    return {
        "id": organization.id,
        "name": organization.name,
        "acronym": organization.acronym,
        "slug": organization.slug,
        "logo": organization.logo,
        "logo_thumbnail": organization.logo_thumbnail,
        "page": organization.page,
        "badges": organization.badges or [],
    }


def _org_dict(organization: Organization) -> dict[str, Any]:
    return {
        **_org_ref(organization),
        "description": organization.description,
        "created_at": organization.created_at,
        "last_modified": organization.last_modified,
        "datasets_count": organization.datasets_count,
        "reuses_count": organization.reuses_count,
        "views": organization.views,
        "followers": organization.followers,
        "zone": organization.zone,
    }


def _resource_dict(resource: Resource) -> dict[str, Any]:
    return {
        "id": resource.id,
        "title": resource.title,
        "description": resource.description,
        "format": resource.format,
        "mime": resource.mime,
        "url": resource.url,
        "filesize": resource.filesize,
        "last_modified": resource.last_modified,
        "created_at": resource.created_at,
        "type": resource.type,
        "preview_url": resource.preview_url,
        "parquet_url": resource.parquet_url,
        "is_tabular": resource.is_tabular,
    }


def _dataset_summary(dataset: Dataset) -> dict[str, Any]:
    return {
        "id": dataset.id,
        "title": dataset.title,
        "slug": dataset.slug,
        "page": dataset.page,
        "description": dataset.description,
        "organization": _org_ref(dataset.organization),
        "license": dataset.license,
        "tags": dataset.tags or [],
        "created_at": dataset.created_at,
        "last_modified": dataset.last_modified,
        "last_update": dataset.last_update,
        "frequency": dataset.frequency,
        "metrics": {
            "views": dataset.views,
            "followers": dataset.followers,
            "reuses": dataset.reuses,
            "discussions": dataset.discussions,
        },
        "resources_count": dataset.resources_count,
        "formats": dataset.formats or [],
        "spatial_granularity": dataset.spatial_granularity,
        "temporal_start": dataset.temporal_start,
        "temporal_end": dataset.temporal_end,
        "quality_score": dataset.quality_score,
    }


def _dataset_detail(dataset: Dataset) -> dict[str, Any]:
    payload = _dataset_summary(dataset)
    resources = sorted(
        dataset.resources or [],
        key=lambda resource: (resource.type != "main", (resource.title or "").lower()),
    )
    payload.update(
        {
            "access_type": dataset.access_type,
            "archived": bool(dataset.archived),
            "spatial_zones": dataset.spatial_zones or [],
            "resources": [_resource_dict(resource) for resource in resources],
            "resources_count": max(dataset.resources_count, len(resources)),
        }
    )
    return payload


class CatalogService:
    """Requetes SQL du catalogue (datasets, organisations, facettes)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _ensure_catalog(self) -> None:
        total = int(
            await self.session.scalar(select(func.count()).select_from(Dataset)) or 0
        )
        if total == 0:
            raise CatalogError(
                "La base de données est vide. Lancez d'abord l'ingestion : "
                "`python -m app.ingest`.",
                status_code=503,
            )

    # ------------------------------------------------------------------ #
    # Jeux de donnees
    # ------------------------------------------------------------------ #
    async def search_datasets(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort: str | None = None,
        organization: str | None = None,
        tag: str | None = None,
        license: str | None = None,
        format: str | None = None,
        format_family: str | None = None,
        producer_type: str | None = None,
        geozone: str | None = None,
        granularity: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure_catalog()
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 100))

        conditions = []
        term = normalize_text(query) if query else ""
        if term:
            conditions.append(Dataset.search_text.like(f"%{term}%"))
        if organization:
            conditions.append(Dataset.organization_id == organization)
        if license:
            conditions.append(Dataset.license == license)
        if producer_type:
            conditions.append(Dataset.producer_type == producer_type)
        if granularity:
            conditions.append(Dataset.spatial_granularity == granularity)
        if tag:
            conditions.append(
                select(DatasetTag.dataset_id)
                .where(DatasetTag.dataset_id == Dataset.id, DatasetTag.tag == tag)
                .exists()
            )
        if format:
            conditions.append(
                select(DatasetFormat.dataset_id)
                .where(
                    DatasetFormat.dataset_id == Dataset.id,
                    DatasetFormat.format == format,
                )
                .exists()
            )
        if format_family:
            conditions.append(
                select(DatasetFormat.dataset_id)
                .where(
                    DatasetFormat.dataset_id == Dataset.id,
                    DatasetFormat.family == format_family,
                )
                .exists()
            )
        # geozone n'est pas indexe dans le catalogue local (filtre non expose UI).
        _ = geozone

        total = int(
            await self.session.scalar(
                select(func.count()).select_from(Dataset).where(*conditions)
            )
            or 0
        )

        statement = (
            select(Dataset)
            .options(selectinload(Dataset.organization))
            .where(*conditions)
        )
        sort_columns = {
            "-created": Dataset.created_at,
            "-last_update": Dataset.last_update,
            "-views": Dataset.views,
            "-followers": Dataset.followers,
            "-reuses": Dataset.reuses,
        }
        if sort in sort_columns:
            statement = statement.order_by(
                sort_columns[sort].desc().nullslast(), Dataset.id
            )
        elif term:
            prefix = (query or "").strip()
            statement = statement.order_by(
                case((Dataset.title.ilike(f"{prefix}%"), 0), else_=1),
                Dataset.last_update.desc().nullslast(),
                Dataset.id,
            )
        else:
            statement = statement.order_by(
                Dataset.last_update.desc().nullslast(), Dataset.id
            )

        statement = statement.offset((page - 1) * page_size).limit(page_size)
        datasets = (await self.session.scalars(statement)).all()

        return {
            "query": query,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, math.ceil(total / page_size)),
            "total_capped": False,
            "sort": sort,
            "data": [_dataset_summary(dataset) for dataset in datasets],
            "facets": {},
        }

    async def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        statement = (
            select(Dataset)
            .options(
                selectinload(Dataset.organization),
                selectinload(Dataset.resources),
            )
            .where(Dataset.id == dataset_id)
        )
        dataset = await self.session.scalar(statement)
        if dataset is None:
            raise CatalogError("Jeu de données introuvable dans le catalogue.", 404)
        return _dataset_detail(dataset)

    # ------------------------------------------------------------------ #
    # Organisations
    # ------------------------------------------------------------------ #
    async def search_organizations(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure_catalog()
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 100))
        term = normalize_text(query) if query else ""

        conditions = []
        if term:
            conditions.append(Organization.search_name.like(f"%{term}%"))

        total = int(
            await self.session.scalar(
                select(func.count()).select_from(Organization).where(*conditions)
            )
            or 0
        )

        order = {
            "-created": Organization.created_at.desc().nullslast(),
            "-followers": Organization.followers.desc().nullslast(),
            "-datasets": Organization.datasets_count.desc().nullslast(),
        }.get(sort or "", Organization.datasets_count.desc().nullslast())

        statement = (
            select(Organization)
            .where(*conditions)
            .order_by(order, Organization.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        organizations = (await self.session.scalars(statement)).all()

        return {
            "query": query,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, math.ceil(total / page_size)),
            "data": [_org_dict(organization) for organization in organizations],
        }

    async def get_organization(self, organization_id: str) -> dict[str, Any]:
        organization = await self.session.get(Organization, organization_id)
        if organization is None:
            raise CatalogError("Organisation introuvable dans le catalogue.", 404)

        statement = (
            select(Dataset)
            .options(selectinload(Dataset.organization))
            .where(Dataset.organization_id == organization_id)
            .order_by(Dataset.last_update.desc().nullslast(), Dataset.id)
            .limit(10)
        )
        latest = (await self.session.scalars(statement)).all()
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Dataset)
                .where(Dataset.organization_id == organization_id)
            )
            or 0
        )

        return {
            "organization": _org_dict(organization),
            "datasets": [_dataset_summary(dataset) for dataset in latest],
            "datasets_total": total,
        }

    # ------------------------------------------------------------------ #
    # Vue d'ensemble
    # ------------------------------------------------------------------ #
    async def _facet(
        self, statement, limit: int = 20
    ) -> list[dict[str, Any]]:
        rows = (await self.session.execute(statement.limit(limit))).all()
        return [
            {"name": str(name), "count": int(count or 0)} for name, count in rows
        ]

    async def get_overview(self) -> dict[str, Any]:
        await self._ensure_catalog()

        totals = {
            "datasets": int(
                await self.session.scalar(select(func.count()).select_from(Dataset)) or 0
            ),
            "organizations": int(
                await self.session.scalar(
                    select(func.count()).select_from(Organization)
                )
                or 0
            ),
        }
        stats = {
            row.key: int(row.value or 0)
            for row in (await self.session.scalars(select(SiteStat))).all()
        }
        totals["reuses"] = stats.get("reuses", 0)
        totals["dataservices"] = stats.get("dataservices", 0)

        organization_rows = (
            await self.session.execute(
                select(
                    Organization.name,
                    Organization.datasets_count,
                    Organization.id,
                )
                .order_by(Organization.datasets_count.desc().nullslast())
                .limit(20)
            )
        ).all()

        licenses = await self._facet(
            select(Dataset.license, func.count())
            .where(Dataset.license.is_not(None), Dataset.license != "")
            .group_by(Dataset.license)
            .order_by(func.count().desc())
        )
        families = await self._facet(
            select(
                DatasetFormat.family,
                func.count(func.distinct(DatasetFormat.dataset_id)),
            )
            .group_by(DatasetFormat.family)
            .order_by(func.count(func.distinct(DatasetFormat.dataset_id)).desc())
        )
        formats = await self._facet(
            select(
                DatasetFormat.format,
                func.count(func.distinct(DatasetFormat.dataset_id)),
            )
            .group_by(DatasetFormat.format)
            .order_by(func.count(func.distinct(DatasetFormat.dataset_id)).desc())
        )
        tags = await self._facet(
            select(DatasetTag.tag, func.count())
            .group_by(DatasetTag.tag)
            .order_by(func.count().desc()),
            limit=20,
        )
        producer_types = await self._facet(
            select(Dataset.producer_type, func.count())
            .group_by(Dataset.producer_type)
            .order_by(func.count().desc())
        )

        latest_statement = (
            select(Dataset)
            .options(selectinload(Dataset.organization))
            .order_by(Dataset.last_update.desc().nullslast(), Dataset.id)
            .limit(6)
        )
        latest = (await self.session.scalars(latest_statement)).all()

        return {
            "totals": totals,
            "facets": {
                "organization_id_with_name": [
                    {
                        "id": str(organization_id),
                        "name": str(name or "Organisation inconnue"),
                        "count": int(count or 0),
                    }
                    for name, count, organization_id in organization_rows
                ],
                "license": licenses,
                "format_family": families,
                "format": formats,
                "tag": tags,
                "producer_type": producer_types,
            },
            "latest_datasets": [_dataset_summary(dataset) for dataset in latest],
        }
