"""Bloom filter on a plain Redis bitmap (works on any Redis, including free hosted tiers
without the RedisBloom module).

A bloom filter answers "definitely not seen" or "maybe seen". It is only ever used as a
fast pre-check in front of an authoritative database lookup, never as the source of truth.
"""

import hashlib
import math

from redis.asyncio import Redis


class BloomFilter:
    def __init__(self, redis: Redis, key: str, capacity: int, error_rate: float) -> None:
        if capacity <= 0 or not 0 < error_rate < 1:
            raise ValueError("capacity must be > 0 and 0 < error_rate < 1")
        self._redis = redis
        self._key = key
        self.size_bits = math.ceil(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        self.hash_count = max(1, round(self.size_bits / capacity * math.log(2)))

    def _offsets(self, item: str) -> list[int]:
        # Kirsch-Mitzenmacher: k hashes derived from two independent 64-bit hashes.
        digest = hashlib.blake2b(item.encode(), digest_size=16).digest()
        h1 = int.from_bytes(digest[:8], "big")
        h2 = int.from_bytes(digest[8:], "big") | 1
        return [(h1 + i * h2) % self.size_bits for i in range(self.hash_count)]

    async def add(self, item: str) -> None:
        pipe = self._redis.pipeline(transaction=False)
        for offset in self._offsets(item):
            pipe.setbit(self._key, offset, 1)
        await pipe.execute()

    async def might_contain(self, item: str) -> bool:
        pipe = self._redis.pipeline(transaction=False)
        for offset in self._offsets(item):
            pipe.getbit(self._key, offset)
        return all(await pipe.execute())
