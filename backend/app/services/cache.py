"""Caches TTL (memoire ou Redis) pour eviter de marteler l'API data.gouv.fr."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from cachetools import TTLCache
from redis.asyncio import Redis

from ..config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T")
_MISSING = object()


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

    async def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

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


class RedisTTLCache:
    """Cache Redis avec repli automatique en memoire si Redis est indisponible."""

    def __init__(self, url: str, ttl: int, namespace: str = "dfe") -> None:
        self._client = Redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        self._ttl = ttl
        self._namespace = namespace
        self._fallback = AsyncTTLCache(maxsize=2048, ttl=ttl)
        self._locks: dict[str, asyncio.Lock] = {}
        self._redis_disabled = False

    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    async def get(self, key: str) -> Any:
        if not self._redis_disabled:
            try:
                raw = await self._client.get(self._key(key))
                if raw is not None:
                    return json.loads(raw)
            except Exception as exc:  # noqa: BLE001 - repli volontaire
                self._redis_disabled = True
                logger.warning("Redis indisponible, cache memoire utilise : %s", exc)
        return await self._fallback.get(key)

    async def set(self, key: str, value: Any) -> None:
        await self._fallback.set(key, value)
        if self._redis_disabled:
            return
        try:
            await self._client.set(
                self._key(key), json.dumps(value, ensure_ascii=False), ex=self._ttl
            )
        except Exception as exc:  # noqa: BLE001 - repli volontaire
            self._redis_disabled = True
            logger.warning("Ecriture Redis impossible, cache memoire utilise : %s", exc)

    async def get_or_create(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        cached = await self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = await self.get(key)
            if cached is not None:
                return cached  # type: ignore[return-value]
            value = await factory()
            await self.set(key, value)
            return value

    def clear(self) -> None:
        self._fallback.clear()

    async def aclose(self) -> None:
        try:
            await self._client.aclose()
        except Exception as exc:  # noqa: BLE001 - fermeture best effort
            logger.debug("Fermeture Redis ignoree : %s", exc)


def build_cache(settings: Settings, namespace: str, ttl: int | None = None):
    """Retourne un cache Redis si configure, sinon un cache memoire."""
    if settings.redis_url:
        return RedisTTLCache(settings.redis_url, ttl or settings.cache_ttl, namespace)
    return AsyncTTLCache(settings.cache_maxsize, ttl or settings.cache_ttl)
