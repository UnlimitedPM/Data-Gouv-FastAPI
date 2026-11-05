"""Modeles Pydantic exposes par l'API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Organisations
# --------------------------------------------------------------------------- #
class OrganizationRef(BaseModel):
    id: str | None = None
    name: str | None = None
    acronym: str | None = None
    slug: str | None = None
    logo: str | None = None
    logo_thumbnail: str | None = None
    page: str | None = None
    badges: list[str] = Field(default_factory=list)


class Organization(OrganizationRef):
    description: str | None = None
    created_at: datetime | None = None
    last_modified: datetime | None = None
    datasets_count: int | None = None
    reuses_count: int | None = None
    views: int | None = None
    followers: int | None = None
    zone: str | None = None


# --------------------------------------------------------------------------- #
# Ressources et jeux de donnees
# --------------------------------------------------------------------------- #
class Resource(BaseModel):
    id: str | None = None
    title: str | None = None
    description: str | None = None
    format: str | None = None
    mime: str | None = None
    url: str | None = None
    filesize: float | None = None
    last_modified: datetime | None = None
    created_at: datetime | None = None
    type: str | None = None
    preview_url: str | None = None
    parquet_url: str | None = None
    is_tabular: bool = False


class DatasetSummary(BaseModel):
    id: str
    title: str
    slug: str | None = None
    page: str | None = None
    description: str | None = None
    organization: OrganizationRef | None = None
    license: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    last_modified: datetime | None = None
    last_update: datetime | None = None
    frequency: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    resources_count: int = 0
    formats: list[str] = Field(default_factory=list)
    spatial_granularity: str | None = None
    temporal_start: str | None = None
    temporal_end: str | None = None
    quality_score: float | None = None


class DatasetDetail(DatasetSummary):
    access_type: str | None = None
    archived: bool = False
    spatial_zones: list[str] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Facettes et resultats de recherche
# --------------------------------------------------------------------------- #
class FacetItem(BaseModel):
    name: str
    count: int = 0
    id: str | None = None
    color: str | None = None


class DatasetSearchResponse(BaseModel):
    query: str | None = None
    page: int
    page_size: int
    total: int
    pages: int
    total_capped: bool = False
    sort: str | None = None
    data: list[DatasetSummary] = Field(default_factory=list)
    facets: dict[str, list[FacetItem]] = Field(default_factory=dict)


class OrganizationSearchResponse(BaseModel):
    query: str | None = None
    page: int
    page_size: int
    total: int
    pages: int
    data: list[Organization] = Field(default_factory=list)


class OrganizationDetail(BaseModel):
    organization: Organization
    datasets: list[DatasetSummary] = Field(default_factory=list)
    datasets_total: int = 0


# --------------------------------------------------------------------------- #
# Statistiques globales
# --------------------------------------------------------------------------- #
class Totals(BaseModel):
    datasets: int = 0
    organizations: int = 0
    reuses: int = 0
    dataservices: int = 0


class OverviewResponse(BaseModel):
    totals: Totals
    facets: dict[str, list[FacetItem]] = Field(default_factory=dict)
    latest_datasets: list[DatasetSummary] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Previsualisation / profilage de fichiers tabulaires
# --------------------------------------------------------------------------- #
class ColumnInfo(BaseModel):
    name: str
    dtype: str


class PreviewResponse(BaseModel):
    dataset_id: str
    resource: Resource
    source: str
    columns: list[ColumnInfo] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    rows_loaded: int = 0
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


class TopValue(BaseModel):
    value: str
    count: int
    pct: float


class ColumnProfile(BaseModel):
    name: str
    kind: str
    dtype: str
    non_null: int
    missing: int
    missing_pct: float
    unique: int | None = None
    stats: dict[str, Any] = Field(default_factory=dict)
    top_values: list[TopValue] = Field(default_factory=list)


class CorrelationMatrix(BaseModel):
    columns: list[str]
    values: list[list[float | None]]


class ProfileResponse(BaseModel):
    dataset_id: str
    resource: Resource
    source: str
    rows_analyzed: int
    truncated: bool = False
    columns: list[ColumnProfile] = Field(default_factory=list)
    numeric_summary: list[dict[str, Any]] = Field(default_factory=list)
    correlation: CorrelationMatrix | None = None
    warnings: list[str] = Field(default_factory=list)
