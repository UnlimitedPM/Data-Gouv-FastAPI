"""Client asynchrone pour l'API publique de data.gouv.fr (v2 + repli v1)."""

from __future__ import annotations

import asyncio
import math
import unicodedata
from typing import Any
from urllib.parse import urlencode

import httpx

from ..config import Settings
from .cache import AsyncTTLCache

DEFAULT_FACETS: tuple[str, ...] = (
    "organization_id_with_name",
    "license",
    "format",
    "format_family",
    "producer_type",
    "tag",
)

TABULAR_FORMATS: frozenset[str] = frozenset(
    {
        "csv",
        "tsv",
        "txt",
        "tab",
        "xls",
        "xlsx",
        "xlsm",
        "json",
        "geojson",
        "ndjson",
        "jsonl",
        "parquet",
    }
)


class DataGouvError(RuntimeError):
    """Erreur de communication ou de lecture avec data.gouv.fr."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


# --------------------------------------------------------------------------- #
# Normalisation des objets renvoyes par data.gouv.fr
# --------------------------------------------------------------------------- #
def _badge_kinds(raw: Any) -> list[str]:
    kinds: list[str] = []
    for badge in raw or []:
        if isinstance(badge, dict) and badge.get("kind"):
            kinds.append(str(badge["kind"]))
        elif isinstance(badge, str):
            kinds.append(badge)
    return kinds


def _slim_org(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "acronym": raw.get("acronym"),
        "slug": raw.get("slug"),
        "logo": raw.get("logo"),
        "logo_thumbnail": raw.get("logo_thumbnail"),
        "page": raw.get("page"),
        "badges": _badge_kinds(raw.get("badges")),
    }


def _resource_format(raw: dict[str, Any]) -> str | None:
    fmt = (raw.get("format") or "").strip().lower()
    if fmt:
        # Certaines ressources declarent "csv, api" ou "xlsx, zip" : on garde
        # le premier format, celui qui decrit le fichier principal.
        return fmt.split(",", 1)[0].strip() or None
    title = (raw.get("title") or "").strip().lower()
    if "." in title:
        return title.rsplit(".", 1)[-1]
    return None


def _slim_resource(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    extras = raw.get("extras") if isinstance(raw.get("extras"), dict) else {}
    fmt = _resource_format(raw)
    parquet_url = extras.get("analysis:parsing:parquet_url")
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "description": raw.get("description"),
        "format": fmt,
        "mime": raw.get("mime"),
        "url": raw.get("url"),
        "filesize": raw.get("filesize"),
        "last_modified": raw.get("last_modified"),
        "created_at": raw.get("created_at"),
        "type": raw.get("type"),
        "preview_url": raw.get("preview_url"),
        "parquet_url": parquet_url if isinstance(parquet_url, str) else None,
        "is_tabular": bool(fmt in TABULAR_FORMATS or parquet_url),
    }


def _slim_dataset(raw: dict[str, Any]) -> dict[str, Any]:
    resources = raw.get("resources")
    resource_list: list[dict[str, Any]] = []
    resources_total = 0

    if isinstance(resources, list):
        resource_list = [r for r in resources if isinstance(r, dict)]
        resources_total = len(resource_list)
    elif isinstance(resources, dict) and isinstance(resources.get("total"), int):
        resources_total = int(resources["total"])

    formats = sorted(
        {
            fmt
            for fmt in (_resource_format(r) for r in resource_list)
            if fmt
        }
    )
    temporal = raw.get("temporal_coverage") or {}
    spatial = raw.get("spatial") or {}
    quality = raw.get("quality") or {}
    metrics = raw.get("metrics") or {}

    return {
        "id": raw.get("id") or raw.get("slug") or "",
        "title": raw.get("title") or "(sans titre)",
        "slug": raw.get("slug"),
        "page": raw.get("page"),
        "description": raw.get("description_short") or raw.get("description"),
        "organization": _slim_org(raw.get("organization")),
        "license": raw.get("license"),
        "tags": raw.get("tags") or [],
        "created_at": raw.get("created_at"),
        "last_modified": raw.get("last_modified"),
        "last_update": raw.get("last_update"),
        "frequency": raw.get("frequency"),
        "metrics": metrics if isinstance(metrics, dict) else {},
        "resources_count": resources_total,
        "formats": formats,
        "spatial_granularity": spatial.get("granularity") if isinstance(spatial, dict) else None,
        "temporal_start": temporal.get("start") if isinstance(temporal, dict) else None,
        "temporal_end": temporal.get("end") if isinstance(temporal, dict) else None,
        "quality_score": quality.get("score") if isinstance(quality, dict) else None,
    }


def _slim_dataset_detail(raw: dict[str, Any]) -> dict[str, Any]:
    dataset = _slim_dataset(raw)
    resources = [
        _slim_resource(r) for r in (raw.get("resources") or []) if isinstance(r, dict)
    ]
    spatial = raw.get("spatial") if isinstance(raw.get("spatial"), dict) else {}
    dataset.update(
        {
            "access_type": raw.get("access_type"),
            "archived": bool(raw.get("archived")),
            "spatial_zones": spatial.get("zones") or [],
            "resources": resources,
        }
    )
    if resources:
        dataset["resources_count"] = max(dataset["resources_count"], len(resources))
        dataset["formats"] = sorted(
            {r["format"] for r in resources if r.get("format")}
        )
    return dataset


def _normalize_text(value: Any) -> str:
    """Minuscule sans accents, pour une recherche tolerante."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def _slim_org_full(raw: dict[str, Any]) -> dict[str, Any]:
    """Organisation + metriques, format commun aux listes et au catalogue."""
    org = _slim_org(raw) or {}
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    org.update(
        {
            "description": raw.get("description"),
            "created_at": raw.get("created_at"),
            "last_modified": raw.get("last_modified"),
            "datasets_count": metrics.get("datasets"),
            "reuses_count": metrics.get("reuses"),
            "views": metrics.get("views"),
            "followers": metrics.get("followers"),
            "zone": raw.get("zone"),
        }
    )
    return org


def _slim_organization_detail(raw: dict[str, Any]) -> dict[str, Any]:
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    org = _slim_org(raw) or {}
    org.update(
        {
            "description": raw.get("description"),
            "created_at": raw.get("created_at"),
            "last_modified": raw.get("last_modified"),
            "datasets_count": metrics.get("datasets"),
            "reuses_count": metrics.get("reuses"),
            "views": metrics.get("views"),
            "followers": metrics.get("followers"),
            "zone": raw.get("zone"),
        }
    )
    return org


def _clean_facets(
    raw_facets: dict[str, Any] | None,
    limit: int = 20,
    allowed: tuple[str, ...] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Nettoie les facettes et retire l'entree speciale ``all``."""
    cleaned: dict[str, list[dict[str, Any]]] = {}

    for key, items in (raw_facets or {}).items():
        if allowed is not None and key not in allowed:
            continue
        if not isinstance(items, list):
            continue
        values: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name or name == "all":
                continue
            entry: dict[str, Any] = {
                "name": str(name),
                "count": int(item.get("count") or 0),
            }
            if key == "organization_id_with_name" and "|" in str(name):
                org_id, label = str(name).split("|", 1)
                entry["id"] = org_id
                entry["name"] = label
            values.append(entry)
        values.sort(key=lambda v: v["count"], reverse=True)
        cleaned[key] = values[:limit]

    return cleaned


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class DataGouvClient:
    """Encapsule les appels HTTP, le cache et la normalisation des donnees."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.http = http
        self._cache = AsyncTTLCache(settings.cache_maxsize, settings.cache_ttl)
        self._org_catalog_cache = AsyncTTLCache(maxsize=1, ttl=6 * 3600)

    # ------------------------------------------------------------------ #
    # Transport
    # ------------------------------------------------------------------ #
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        url = f"{self.settings.datagouv_api_base.rstrip('/')}/{path.lstrip('/')}"
        key = f"{url}?{urlencode(sorted(params.items()))}"

        async def fetch() -> Any:
            try:
                response = await self.http.get(url, params=params)
            except httpx.HTTPError as exc:
                raise DataGouvError(
                    f"data.gouv.fr injoignable ({exc.__class__.__name__}). "
                    "Verifiez votre connexion reseau."
                ) from exc

            if response.status_code >= 400:
                raise DataGouvError(
                    f"data.gouv.fr a renvoye une erreur {response.status_code}.",
                    status_code=502,
                )

            try:
                return response.json()
            except ValueError as exc:
                raise DataGouvError("Reponse JSON invalide de data.gouv.fr.") from exc

        return await self._cache.get_or_create(key, fetch)

    async def _count(self, path: str) -> int:
        payload = await self._get(path, {"page": 1, "page_size": 1})
        try:
            return int(payload.get("total") or 0)
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------ #
    # Facettes
    # ------------------------------------------------------------------ #
    async def _build_facets(
        self, raw_facets: Any, limit: int = 20
    ) -> dict[str, list[dict[str, Any]]]:
        raw_facets = raw_facets if isinstance(raw_facets, dict) else {}
        return _clean_facets(raw_facets, limit=limit, allowed=DEFAULT_FACETS)

    # ------------------------------------------------------------------ #
    # Recherche de jeux de donnees
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
        facets: list[str] | None = None,
        include_facets: bool = False,
    ) -> dict[str, Any]:
        """Recherche des jeux de donnees via l'API v2 (moteur de recherche actuel).

        L'API v2 plafonne ``total`` a 10 000 resultats ; ``total_capped`` permet
        au frontend de l'indiquer. En cas d'indisponibilite, repli sur l'API v1
        (totaux exacts mais ressources completes et pertinence plus ancienne).
        """
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 100))
        facet_param = ",".join(facets or DEFAULT_FACETS)

        filters: dict[str, Any] = {
            "q": query,
            "sort": sort,
            "organization": organization,
            "tag": tag,
            "license": license,
            "format": format,
            "format_family": format_family,
            "producer_type": producer_type,
            "geozone": geozone,
            "granularity": granularity,
        }
        filters = {key: value for key, value in filters.items() if value}
        common: dict[str, Any] = {"page": page, "page_size": page_size, **filters}
        used_v2 = True

        try:
            raw = await self._get(
                "2/datasets/search/", {**common, "facets": facet_param}
            )
        except DataGouvError:
            raw = await self._get("1/datasets/", common)
            used_v2 = False

        items = [
            _slim_dataset(row)
            for row in (raw.get("data") or [])
            if isinstance(row, dict)
        ]
        total = int(raw.get("total") or len(items))

        # L'API v2 plafonne le total a 10 000 resultats.
        total_capped = used_v2 and total >= 10_000

        facets_payload: dict[str, list[dict[str, Any]]] = {}
        if include_facets:
            facets_payload = await self._build_facets(raw.get("facets"))

        return {
            "query": query,
            "page": int(raw.get("page") or page),
            "page_size": page_size,
            "total": total,
            "pages": max(1, -(-total // page_size)),
            "total_capped": total_capped,
            "sort": sort,
            "data": items,
            "facets": facets_payload,
        }

    # ------------------------------------------------------------------ #
    # Detail d'un jeu de donnees
    # ------------------------------------------------------------------ #
    async def _fetch_resources(self, dataset_id: str) -> list[dict[str, Any]]:
        first = await self._get(
            f"2/datasets/{dataset_id}/resources/", {"page": 1, "page_size": 100}
        )
        items = [r for r in (first.get("data") or []) if isinstance(r, dict)]
        total = int(first.get("total") or len(items))

        page = 2
        while len(items) < min(total, 500) and page <= 5:
            nxt = await self._get(
                f"2/datasets/{dataset_id}/resources/",
                {"page": page, "page_size": 100},
            )
            batch = [r for r in (nxt.get("data") or []) if isinstance(r, dict)]
            if not batch:
                break
            items.extend(batch)
            page += 1

        return items

    async def get_dataset_bundle(self, dataset_id: str) -> dict[str, Any]:
        """Retourne le detail complet d'un dataset + toutes ses ressources."""
        detail: dict[str, Any]
        resources: list[dict[str, Any]]

        try:
            detail, resources = await asyncio.gather(
                self._get(f"2/datasets/{dataset_id}/"),
                self._fetch_resources(dataset_id),
            )
        except DataGouvError as first_error:
            try:
                raw = await self._get(f"1/datasets/{dataset_id}/")
            except DataGouvError as exc:
                raise DataGouvError(
                    "Jeu de donnees introuvable sur data.gouv.fr.",
                    status_code=404,
                ) from exc
            detail = raw
            resources = [r for r in (raw.get("resources") or []) if isinstance(r, dict)]
            _ = first_error

        combined = dict(detail)
        combined["resources"] = resources
        return _slim_dataset_detail(combined)

    # ------------------------------------------------------------------ #
    # Organisations
    # ------------------------------------------------------------------ #
    async def _org_catalog(self) -> list[dict[str, Any]]:
        """Catalogue complet des organisations (mis en cache une heure).

        L'API amont ne gere pas la recherche par prefixe (``biodiv`` ne renvoie
        rien alors que ``biodiversite`` fonctionne). Pour la recherche en direct,
        on indexe donc toutes les organisations une fois, puis on filtre par
        sous-chaine sans tenir compte des accents.
        """

        async def load() -> list[dict[str, Any]]:
            page_size = 1000
            first = await self._get(
                "2/organizations/search/",
                {"page": 1, "page_size": page_size, "sort": "-datasets"},
            )
            total = int(first.get("total") or 0)
            rows = [row for row in first.get("data") or [] if isinstance(row, dict)]
            pages = min(10, math.ceil(total / page_size))
            if pages > 1:
                batches = await asyncio.gather(
                    *(
                        self._get(
                            "2/organizations/search/",
                            {"page": page, "page_size": page_size, "sort": "-datasets"},
                        )
                        for page in range(2, pages + 1)
                    )
                )
                for batch in batches:
                    rows.extend(
                        row for row in batch.get("data") or [] if isinstance(row, dict)
                    )
            return rows

        return await self._org_catalog_cache.get_or_create("catalog", load)

    async def warm_organization_catalog(self) -> None:
        """Precharge le catalogue pour que la recherche en direct soit immediate."""
        try:
            await self._org_catalog()
        except DataGouvError:
            # Le prechargement est un confort : une erreur ne doit pas bloquer l'API.
            return

    async def _search_org_catalog(
        self,
        query: str,
        page: int,
        page_size: int,
        sort: str | None,
    ) -> dict[str, Any]:
        catalog = await self._org_catalog()
        needle = _normalize_text(query)
        items: list[dict[str, Any]] = []

        for row in catalog:
            haystack = " ".join(
                _normalize_text(row.get(field)) for field in ("name", "acronym", "slug")
            )
            if needle and needle in haystack:
                items.append(_slim_org_full(row))

        if sort == "-followers":
            items.sort(key=lambda org: org.get("followers") or 0, reverse=True)
        elif sort == "-created":
            items.sort(key=lambda org: org.get("created_at") or "", reverse=True)
        else:
            items.sort(key=lambda org: org.get("datasets_count") or 0, reverse=True)

        total = len(items)
        start = (page - 1) * page_size
        return {
            "query": query,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, -(-total // page_size)),
            "data": items[start : start + page_size],
        }

    async def search_organizations(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort: str | None = None,
    ) -> dict[str, Any]:
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 100))
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if query:
            params["q"] = query
        if sort:
            params["sort"] = sort

        raw = await self._get("2/organizations/search/", params)
        items = [
            _slim_org_full(row)
            for row in raw.get("data") or []
            if isinstance(row, dict)
        ]
        total = int(raw.get("total") or len(items))

        # Repli sur le catalogue local pour les recherches partielles.
        if query and total == 0:
            return await self._search_org_catalog(query, page, page_size, sort)

        return {
            "query": query,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, -(-total // page_size)),
            "data": items,
        }

    async def get_organization(self, organization_id: str) -> dict[str, Any]:
        try:
            org_raw, datasets = await asyncio.gather(
                self._get(f"1/organizations/{organization_id}/"),
                self.search_datasets(
                    organization=organization_id, page=1, page_size=10, sort="-created"
                ),
            )
        except DataGouvError as exc:
            raise DataGouvError(
                "Organisation introuvable sur data.gouv.fr.", status_code=404
            ) from exc

        return {
            "organization": _slim_organization_detail(org_raw),
            "datasets": datasets["data"],
            "datasets_total": datasets["total"],
        }

    # ------------------------------------------------------------------ #
    # Statistiques globales
    # ------------------------------------------------------------------ #
    async def _latest_datasets(self) -> list[dict[str, Any]]:
        """Les derniers datasets, avec ressources inline (v1) pour les formats."""
        try:
            raw = await self._get(
                "1/datasets/", {"page": 1, "page_size": 6, "sort": "-created"}
            )
            return [
                _slim_dataset(row)
                for row in (raw.get("data") or [])
                if isinstance(row, dict)
            ]
        except DataGouvError:
            result = await self.search_datasets(page=1, page_size=6, sort="-created")
            return result["data"]

    async def _overview_facets(self) -> dict[str, list[dict[str, Any]]]:
        try:
            raw = await self._get(
                "2/datasets/search/",
                {
                    "page": 1,
                    "page_size": 1,
                    "facets": ",".join(DEFAULT_FACETS),
                },
            )
        except DataGouvError:
            return {}
        return await self._build_facets(raw.get("facets"))

    async def get_overview(self) -> dict[str, Any]:
        latest, facets, datasets, organizations, reuses, dataservices = (
            await asyncio.gather(
                self._latest_datasets(),
                self._overview_facets(),
                self._count("1/datasets/"),
                self._count("2/organizations/search/"),
                self._count("2/reuses/search/"),
                self._count("2/dataservices/search/"),
            )
        )

        return {
            "totals": {
                "datasets": datasets,
                "organizations": organizations,
                "reuses": reuses,
                "dataservices": dataservices,
            },
            "facets": facets,
            "latest_datasets": latest,
        }
