"""Small JSON cache over Redis with namespace versioning.

Invalidation strategy: keys embed a namespace version; bumping the version (one INCR)
makes every older key unreachable, and they expire on their own TTL.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import orjson
from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)


class Cache:
    def __init__(self, redis: Redis, prefix: str = "cache") -> None:
        self._redis = redis
        self._prefix = prefix

    async def _version(self, namespace: str) -> int:
        value = await self._redis.get(f"{self._prefix}:ver:{namespace}")
        return int(value or 0)

    async def bump(self, namespace: str) -> None:
        try:
            await self._redis.incr(f"{self._prefix}:ver:{namespace}")
        except RedisError:
            log.warning("cache bump failed for %s", namespace, exc_info=True)

    async def get_or_set(self, namespace: str, key: str, ttl_seconds: int, loader: Callable[[], Awaitable[Any]]) -> Any:
        """Cache-aside. Redis failures degrade to calling the loader, never to an error."""
        try:
            full_key = f"{self._prefix}:{namespace}:{await self._version(namespace)}:{key}"
            cached = await self._redis.get(full_key)
            if cached is not None:
                return orjson.loads(cached)
        except RedisError:
            log.warning("cache read failed", exc_info=True)
            return await loader()
        value = await loader()
        try:
            await self._redis.set(full_key, orjson.dumps(value), ex=ttl_seconds)
        except RedisError:
            log.warning("cache write failed", exc_info=True)
        return value
