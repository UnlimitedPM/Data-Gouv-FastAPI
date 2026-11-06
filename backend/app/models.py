"""Modeles SQLAlchemy du catalogue local data.gouv.fr."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512), index=True)
    search_name: Mapped[str | None] = mapped_column(Text, index=True)
    acronym: Mapped[str | None] = mapped_column(String(128))
    slug: Mapped[str | None] = mapped_column(String(256))
    logo: Mapped[str | None] = mapped_column(Text)
    logo_thumbnail: Mapped[str | None] = mapped_column(Text)
    page: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    badges: Mapped[list[str]] = mapped_column(JSON, default=list)
    datasets_count: Mapped[int] = mapped_column(Integer, default=0)
    reuses_count: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    zone: Mapped[str | None] = mapped_column(String(128))

    datasets: Mapped[list[Dataset]] = relationship(back_populates="organization")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text, index=True)
    slug: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    search_text: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[str | None] = mapped_column(Text)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    license: Mapped[str | None] = mapped_column(String(64), index=True)
    frequency: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    views: Mapped[int] = mapped_column(Integer, default=0, index=True)
    followers: Mapped[int] = mapped_column(Integer, default=0, index=True)
    reuses: Mapped[int] = mapped_column(Integer, default=0, index=True)
    discussions: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float | None] = mapped_column(Float)
    temporal_start: Mapped[str | None] = mapped_column(String(64))
    temporal_end: Mapped[str | None] = mapped_column(String(64))
    spatial_granularity: Mapped[str | None] = mapped_column(String(128), index=True)
    spatial_zones: Mapped[list[str]] = mapped_column(JSON, default=list)
    access_type: Mapped[str | None] = mapped_column(String(64))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    resources_count: Mapped[int] = mapped_column(Integer, default=0)
    producer_type: Mapped[str] = mapped_column(String(64), default="not-specified", index=True)
    formats: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    organization: Mapped[Organization | None] = relationship(back_populates="datasets")
    resources: Mapped[list[Resource]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class Resource(Base):
    __tablename__ = "resources"

    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str | None] = mapped_column(String(64))
    mime: Mapped[str | None] = mapped_column(String(128))
    url: Mapped[str | None] = mapped_column(Text)
    filesize: Mapped[float | None] = mapped_column(Float)
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    type: Mapped[str | None] = mapped_column(String(64))
    preview_url: Mapped[str | None] = mapped_column(Text)
    parquet_url: Mapped[str | None] = mapped_column(Text)
    is_tabular: Mapped[bool] = mapped_column(Boolean, default=False)

    dataset: Mapped[Dataset] = relationship(back_populates="resources")


class DatasetFormat(Base):
    __tablename__ = "dataset_formats"

    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True
    )
    format: Mapped[str] = mapped_column(String(64), primary_key=True)
    family: Mapped[str] = mapped_column(String(64), index=True)


class DatasetTag(Base):
    __tablename__ = "dataset_tags"

    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(String(256), primary_key=True, index=True)


class SiteStat(Base):
    __tablename__ = "site_stats"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running")
    datasets_count: Mapped[int] = mapped_column(Integer, default=0)
    organizations_count: Mapped[int] = mapped_column(Integer, default=0)
    resources_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
