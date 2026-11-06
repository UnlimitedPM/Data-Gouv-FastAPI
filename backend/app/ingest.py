"""Ingestion du catalogue data.gouv.fr dans la base locale.

Usage :
    python -m app.ingest                # catalogue complet
    python -m app.ingest --limit 5000   # echantillon pour les tests

L'API officielle n'est appelee qu'ici. L'application ne fait ensuite que lire
la base SQLite/PostgreSQL locale.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import SessionLocal, init_db
from .models import (
    Dataset,
    DatasetFormat,
    DatasetTag,
    IngestionRun,
    Organization,
    Resource,
    SiteStat,
)
from .services.datagouv import TABULAR_FORMATS, DataGouvClient, _resource_format
from .utils import normalize_text

logger = logging.getLogger("dfe.ingest")

GEO_FORMATS = {
    "geojson",
    "gpkg",
    "shp",
    "kml",
    "gml",
    "geotiff",
    "tif",
    "tiff",
    "wms",
    "wfs",
}
DOCUMENT_FORMATS = {"pdf", "doc", "docx", "odt", "rtf", "ppt", "pptx"}
MACHINE_FORMATS = {"json", "xml", "rdf", "api", "rss", "atom", "ndjson", "parquet"}


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        # Python 3.11+ accepte directement le suffixe "Z" des dates ISO.
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_family(fmt: str | None) -> str:
    if not fmt:
        return "other"
    if fmt in TABULAR_FORMATS:
        return "tabular"
    if fmt in GEO_FORMATS:
        return "geographical"
    if fmt in DOCUMENT_FORMATS:
        return "documents"
    if fmt in MACHINE_FORMATS:
        return "machine_readable"
    return "other"


def _badges(raw: dict[str, Any]) -> list[str]:
    badges = []
    for badge in raw.get("badges") or []:
        if isinstance(badge, dict) and badge.get("kind"):
            badges.append(str(badge["kind"]))
        elif isinstance(badge, str):
            badges.append(badge)
    return badges


def _producer_type(organization: dict[str, Any]) -> str:
    badges = set(_badges(organization))
    if "public-service" in badges:
        return "public-service"
    if "local-authority" in badges:
        return "local-authority"
    name = normalize_text(organization.get("name"))
    local_tokens = (
        "commune",
        "ville",
        "departement",
        "region",
        "agglomeration",
        "metropole",
        "conseil departemental",
        "conseil regional",
    )
    if any(token in name for token in local_tokens):
        return "local-authority"
    return "not-specified"


def _org_row(raw: dict[str, Any], minimal: bool = False) -> dict[str, Any]:
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    name = raw.get("name")
    acronym = raw.get("acronym")
    slug = raw.get("slug")
    return {
        "id": str(raw.get("id")),
        "name": name,
        "search_name": normalize_text(" ".join(filter(None, [name, acronym, slug]))),
        "acronym": acronym,
        "slug": slug,
        "logo": raw.get("logo"),
        "logo_thumbnail": raw.get("logo_thumbnail"),
        "page": raw.get("page"),
        "description": None if minimal else raw.get("description"),
        "badges": _badges(raw),
        "datasets_count": 0 if minimal else _int(metrics.get("datasets")),
        "reuses_count": 0 if minimal else _int(metrics.get("reuses")),
        "views": 0 if minimal else _int(metrics.get("views")),
        "followers": 0 if minimal else _int(metrics.get("followers")),
        "created_at": None if minimal else _dt(raw.get("created_at")),
        "last_modified": None if minimal else _dt(raw.get("last_modified")),
        "zone": raw.get("zone"),
    }


def _dataset_row(raw: dict[str, Any]) -> dict[str, Any]:
    organization = raw.get("organization") if isinstance(raw.get("organization"), dict) else {}
    tags = list(dict.fromkeys(str(tag) for tag in (raw.get("tags") or []) if tag))
    resources = [r for r in (raw.get("resources") or []) if isinstance(r, dict)]
    formats = sorted(
        {fmt for fmt in (_resource_format(resource) for resource in resources) if fmt}
    )
    temporal = raw.get("temporal_coverage") if isinstance(raw.get("temporal_coverage"), dict) else {}
    spatial = raw.get("spatial") if isinstance(raw.get("spatial"), dict) else {}
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    quality = raw.get("quality") if isinstance(raw.get("quality"), dict) else {}
    title = raw.get("title") or "(sans titre)"
    description = raw.get("description") or ""

    return {
        "id": str(raw.get("id")),
        "title": title,
        "slug": raw.get("slug"),
        "description": description,
        "search_text": normalize_text(" ".join([title, description, *tags])),
        "page": raw.get("page"),
        "organization_id": str(organization["id"])
        if organization.get("id")
        else None,
        "license": raw.get("license"),
        "frequency": raw.get("frequency"),
        "created_at": _dt(raw.get("created_at")),
        "last_modified": _dt(raw.get("last_modified")),
        "last_update": _dt(raw.get("last_update") or raw.get("last_modified")),
        "views": _int(metrics.get("views")),
        "followers": _int(metrics.get("followers")),
        "reuses": _int(metrics.get("reuses")),
        "discussions": _int(metrics.get("discussions")),
        "quality_score": quality.get("score"),
        "temporal_start": temporal.get("start"),
        "temporal_end": temporal.get("end"),
        "spatial_granularity": spatial.get("granularity"),
        "spatial_zones": spatial.get("zones") or [],
        "access_type": raw.get("access_type"),
        "archived": bool(raw.get("archived")),
        "resources_count": len(resources),
        "producer_type": _producer_type(organization),
        "formats": formats,
        "tags": tags,
    }


def _resource_rows(dataset_id: str, raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    resources = [r for r in (raw.get("resources") or []) if isinstance(r, dict)]
    seen_ids: set[str] = set()
    for index, resource in enumerate(resources):
        fmt = _resource_format(resource)
        extras = resource.get("extras") if isinstance(resource.get("extras"), dict) else {}
        parquet_url = extras.get("analysis:parsing:parquet_url")
        resource_id = str(resource.get("id") or f"{dataset_id}-r{index}")
        if resource_id in seen_ids:
            resource_id = f"{resource_id}-{index}"
        seen_ids.add(resource_id)
        rows.append(
            {
                "dataset_id": dataset_id,
                "id": resource_id,
                "title": resource.get("title"),
                "description": resource.get("description"),
                "format": fmt,
                "mime": resource.get("mime"),
                "url": resource.get("url"),
                "filesize": resource.get("filesize"),
                "last_modified": _dt(resource.get("last_modified")),
                "created_at": _dt(resource.get("created_at")),
                "type": resource.get("type"),
                "preview_url": resource.get("preview_url"),
                "parquet_url": parquet_url if isinstance(parquet_url, str) else None,
                "is_tabular": bool(fmt in TABULAR_FORMATS or parquet_url),
            }
        )
    return rows


async def _bulk_insert(
    session: AsyncSession, model: Any, rows: list[dict[str, Any]], chunk_size: int = 500
) -> None:
    for start in range(0, len(rows), chunk_size):
        await session.execute(insert(model), rows[start : start + chunk_size])


async def ingest_catalog(
    client: DataGouvClient,
    limit: int | None = None,
    page_size: int = 1000,
) -> dict[str, Any]:
    """Remplace le catalogue local par un instantane data.gouv.fr."""
    started = datetime.now(UTC)

    logger.info("Recuperation des organisations...")
    organizations_raw = await client._org_catalog()
    organizations: dict[str, dict[str, Any]] = {}
    for raw_organization in organizations_raw:
        if isinstance(raw_organization, dict) and raw_organization.get("id"):
            organizations[str(raw_organization["id"])] = _org_row(raw_organization)

    total_datasets = await client._count("1/datasets/")
    total_pages = max(1, math.ceil(total_datasets / page_size))
    logger.info(
        "Catalogue annonce : %s jeux de donnees, %s organisations, %s pages",
        total_datasets,
        len(organizations),
        total_pages,
    )

    async with SessionLocal() as session:
        run = IngestionRun(started_at=started, status="running")
        session.add(run)
        await session.commit()
        run_id = run.id

        datasets_count = 0
        resources_count = 0

        try:
            async with session.begin():
                # Table de travail vide : un echec annule tout et conserve l'ancien catalogue.
                await session.execute(delete(DatasetTag))
                await session.execute(delete(DatasetFormat))
                await session.execute(delete(Resource))
                await session.execute(delete(Dataset))
                await session.execute(delete(Organization))
                await session.execute(delete(SiteStat))

                await _bulk_insert(session, Organization, list(organizations.values()))

                seen_datasets: set[str] = set()
                for page in range(1, total_pages + 1):
                    if limit is not None and datasets_count >= limit:
                        break

                    payload = await client._get(
                        "1/datasets/", {"page": page, "page_size": page_size}
                    )
                    batch = [
                        raw for raw in (payload.get("data") or []) if isinstance(raw, dict)
                    ]
                    if not batch:
                        break

                    dataset_rows: list[dict[str, Any]] = []
                    resource_rows: list[dict[str, Any]] = []
                    format_rows: list[dict[str, Any]] = []
                    tag_rows: list[dict[str, Any]] = []
                    new_organizations: list[dict[str, Any]] = []

                    for raw_dataset in batch:
                        if limit is not None and datasets_count >= limit:
                            break
                        dataset_id = str(raw_dataset.get("id") or "")
                        if not dataset_id or dataset_id in seen_datasets:
                            continue
                        seen_datasets.add(dataset_id)

                        organization = (
                            raw_dataset.get("organization")
                            if isinstance(raw_dataset.get("organization"), dict)
                            else {}
                        )
                        organization_id = organization.get("id")
                        if organization_id and str(organization_id) not in organizations:
                            organizations[str(organization_id)] = _org_row(
                                organization, minimal=True
                            )
                            new_organizations.append(organizations[str(organization_id)])
                        elif not organization_id:
                            raw_dataset["organization"] = {}

                        row = _dataset_row(raw_dataset)
                        dataset_rows.append(row)
                        datasets_count += 1

                        for resource_row in _resource_rows(dataset_id, raw_dataset):
                            resource_rows.append(resource_row)
                            resources_count += 1

                        for fmt in row["formats"]:
                            format_rows.append(
                                {
                                    "dataset_id": dataset_id,
                                    "format": fmt,
                                    "family": _format_family(fmt),
                                }
                            )
                        for tag in row["tags"]:
                            tag_rows.append({"dataset_id": dataset_id, "tag": tag})

                    if new_organizations:
                        await _bulk_insert(session, Organization, new_organizations)
                    if dataset_rows:
                        await _bulk_insert(session, Dataset, dataset_rows)
                        await _bulk_insert(session, Resource, resource_rows)
                        await _bulk_insert(session, DatasetFormat, format_rows)
                        await _bulk_insert(session, DatasetTag, tag_rows)

                    logger.info(
                        "Page %s/%s : %s jeux de donnees, %s ressources",
                        page,
                        total_pages,
                        datasets_count,
                        resources_count,
                    )

                stats = {
                    "datasets": total_datasets,
                    "organizations": len(organizations),
                    "reuses": await client._count("2/reuses/search/"),
                    "dataservices": await client._count("2/dataservices/search/"),
                }
                await _bulk_insert(
                    session,
                    SiteStat,
                    [
                        {"key": key, "value": value, "updated_at": datetime.now(UTC)}
                        for key, value in stats.items()
                    ],
                )

            async with SessionLocal() as update_session:
                run = await update_session.get(IngestionRun, run_id)
                if run is not None:
                    run.status = "success"
                    run.finished_at = datetime.now(UTC)
                    run.datasets_count = datasets_count
                    run.organizations_count = len(organizations)
                    run.resources_count = resources_count
                    run.extra = stats
                    await update_session.commit()

            logger.info(
                "Ingestion terminee : %s jeux de donnees, %s ressources, %s organisations",
                datasets_count,
                resources_count,
                len(organizations),
            )
            return {
                "datasets": datasets_count,
                "resources": resources_count,
                "organizations": len(organizations),
                "stats": stats,
            }

        except Exception as exc:
            async with SessionLocal() as update_session:
                run = await update_session.get(IngestionRun, run_id)
                if run is not None:
                    run.status = "failed"
                    run.finished_at = datetime.now(UTC)
                    run.datasets_count = datasets_count
                    run.organizations_count = len(organizations)
                    run.resources_count = resources_count
                    run.error = str(exc)[:4000]
                    await update_session.commit()
            logger.exception("Ingestion echouee")
            raise


async def _run(limit: int | None, page_size: int) -> None:
    settings = get_settings()
    await init_db()
    http = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout, connect=10.0),
        headers={"User-Agent": settings.http_user_agent, "Accept": "application/json"},
        follow_redirects=True,
    )
    client = DataGouvClient(settings, http)
    try:
        await ingest_catalog(client, limit=limit, page_size=page_size)
    finally:
        await client.aclose()
        await http.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion du catalogue data.gouv.fr")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre maximum de jeux de donnees (utile pour un test rapide)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Taille des pages de l'API data.gouv.fr (defaut : 1000)",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    asyncio.run(_run(args.limit, max(1, min(args.page_size, 1000))))


if __name__ == "__main__":
    main()
