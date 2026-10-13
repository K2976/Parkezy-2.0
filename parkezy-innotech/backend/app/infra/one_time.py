from redis.asyncio import Redis


class OneTimeTokenRegistry:
    """Exact replay protection: each token id can be consumed once while it is valid."""

    def __init__(self, redis: Redis, prefix: str = "used") -> None:
        self._redis = redis
        self._prefix = prefix

    async def consume(self, namespace: str, token_id: str, ttl_seconds: int) -> bool:
        """True the first time a token id is seen, False on any replay."""
        return bool(await self._redis.set(f"{self._prefix}:{namespace}:{token_id}", 1, nx=True, ex=ttl_seconds))
