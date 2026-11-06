"""Connexion a la base de donnees locale (SQLite par defaut)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base declarative SQLAlchemy."""


engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


async def init_db() -> None:
    """Cree les tables si elles n'existent pas."""
    from . import models  # noqa: F401 - enregistre les modeles aupres du metadata

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def session_dependency() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
