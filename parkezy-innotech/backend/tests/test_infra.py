"""Redis-backed building blocks against a real Redis."""

import uuid

from redis.asyncio import Redis

from app.core.errors import RateLimited
from app.infra.bloom import BloomFilter
from app.infra.cache import Cache
from app.infra.one_time import OneTimeTokenRegistry
from app.infra.rate_limit import RateLimiter
from tests.conftest import make_settings


async def _redis() -> Redis:
    r = Redis.from_url(make_settings().redis_url)
    return r


async def test_bloom_filter_has_no_false_negatives_and_low_false_positives():
    redis = await _redis()
    bloom = BloomFilter(redis, f"test:bloom:{uuid.uuid4().hex}", capacity=2000, error_rate=0.01)
    added = [uuid.uuid4().hex for _ in range(2000)]
    for item in added:
        await bloom.add(item)
    assert all([await bloom.might_contain(i) for i in added])
    unseen = [uuid.uuid4().hex for _ in range(2000)]
    false_positives = sum([await bloom.might_contain(i) for i in unseen])
    assert false_positives / len(unseen) < 0.03
    await redis.aclose()


async def test_rate_limiter_blocks_after_limit():
    redis = await _redis()
    limiter = RateLimiter(redis, prefix=f"rl-{uuid.uuid4().hex}")
    for _ in range(3):
        await limiter.hit("login", "1.2.3.4", 3, 60)
    try:
        await limiter.hit("login", "1.2.3.4", 3, 60)
        raise AssertionError("expected RateLimited")
    except RateLimited as e:
        assert e.details["retry_after_seconds"] > 0
    await limiter.hit("login", "5.6.7.8", 3, 60)  # other identities unaffected
    await redis.aclose()


async def test_cache_versioned_invalidation():
    redis = await _redis()
    cache = Cache(redis, prefix=f"c-{uuid.uuid4().hex}")
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return {"n": calls}

    assert await cache.get_or_set("ns", "k", 30, loader) == {"n": 1}
    assert await cache.get_or_set("ns", "k", 30, loader) == {"n": 1}
    await cache.bump("ns")
    assert await cache.get_or_set("ns", "k", 30, loader) == {"n": 2}
    await redis.aclose()


async def test_one_time_tokens_reject_replay():
    redis = await _redis()
    registry = OneTimeTokenRegistry(redis, prefix=f"ot-{uuid.uuid4().hex}")
    assert await registry.consume("qr", "abc", 60)
    assert not await registry.consume("qr", "abc", 60)
    await redis.aclose()


async def test_cache_degrades_gracefully_when_redis_down():
    broken = Redis.from_url("redis://127.0.0.1:1/0", socket_connect_timeout=0.2)
    cache = Cache(broken)

    async def loader():
        return [1, 2, 3]

    assert await cache.get_or_set("ns", "k", 30, loader) == [1, 2, 3]
    limiter = RateLimiter(broken)
    await limiter.hit("b", "id", 1, 60)  # fails open
    await broken.aclose()
