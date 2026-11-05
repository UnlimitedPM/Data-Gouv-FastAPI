"""Petit cache TTL asynchrone pour eviter de marteler l'API data.gouv.fr."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from cachetools import TTLCache

T = TypeVar("T")


class AsyncTTLCache:
    """Cache TTL avec verrou par cle (evite les appels concurrents en doublon)."""

    def __init__(self, maxsize: int = 512, ttl: int = 300) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._locks: dict[str, asyncio.Lock] = {}

    async def get(self, key: str) -> Any | None:
        try:
            return self._cache[key]
        except KeyError:
            return None

    async def get_or_create(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        """Retourne la valeur en cache ou la calcule via ``factory``."""
        try:
            return self._cache[key]  # type: ignore[return-value]
        except KeyError:
            pass

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            try:
                return self._cache[key]  # type: ignore[return-value]
            except KeyError:
                pass

            value = await factory()
            self._cache[key] = value
            return value

    def clear(self) -> None:
        self._cache.clear()
