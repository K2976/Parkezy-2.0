"""Sliding-window-counter rate limiter (System Design Interview, ch. 4).

A fixed window lets a client burst 2x the limit across a window edge. The sliding window
counter fixes that cheaply: requests in the current window plus the previous window's
count weighted by how much of it still overlaps the rolling window.

    estimated = current + previous * (1 - elapsed_fraction_of_current_window)

Two small Redis counters per client; fails open if Redis is unavailable (availability over
strictness). Brute-force-sensitive checks also have attempt limits in the database.
"""

import logging
import math
import time
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.errors import RateLimited

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitStatus:
    limit: int
    remaining: int
    reset_seconds: int


class RateLimiter:
    def __init__(self, redis: Redis, prefix: str = "rl") -> None:
        self._redis = redis
        self._prefix = prefix

    async def hit(self, bucket: str, identity: str, limit: int, window_seconds: int) -> RateLimitStatus:
        now = time.time()
        window = int(now // window_seconds)
        elapsed = (now % window_seconds) / window_seconds
        current_key = f"{self._prefix}:{bucket}:{identity}:{window}"
        previous_key = f"{self._prefix}:{bucket}:{identity}:{window - 1}"
        reset = math.ceil(window_seconds - now % window_seconds)
        try:
            pipe = self._redis.pipeline(transaction=True)
            pipe.incr(current_key)
            pipe.expire(current_key, window_seconds * 2)
            pipe.get(previous_key)
            current, _, previous = await pipe.execute()
        except RedisError:
            log.warning("rate limiter unavailable", exc_info=True)
            return RateLimitStatus(limit, limit, reset)
        estimated = int(current) + int(previous or 0) * (1 - elapsed)
        remaining = max(0, math.floor(limit - estimated))
        if estimated > limit:
            raise RateLimited(
                "Too many requests, try again shortly",
                details={"retry_after_seconds": reset, "limit": limit},
            )
        return RateLimitStatus(limit, remaining, reset)
