"""Redis-backed building blocks against a real Redis."""

import uuid

from redis.asyncio import Redis

from app.core.errors import RateLimited
from app.infra.bloom import BloomFilter
from app.infra.cache import Cache
from app.infra.one_time import OneTimeTokenRegistry
from app.infra.rate_limit import RateLimiter
from tests.conftest import Harness, make_settings


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


def test_provider_database_urls_are_normalized_for_asyncpg():
    neon = "postgresql://u:p@ep-x-pooler.c-7.us-east-2.aws.neon.tech/db?sslmode=require&channel_binding=require"
    settings = make_settings(database_url=neon)
    assert settings.database_url == "postgresql+asyncpg://u:p@ep-x-pooler.c-7.us-east-2.aws.neon.tech/db?ssl=require"
    assert settings.pgbouncer_for(settings.database_url)
    assert not settings.pgbouncer_for("postgresql+asyncpg://u:p@ep-x.c-7.us-east-2.aws.neon.tech/db")
    assert not make_settings(database_url=neon, db_pgbouncer=False).pgbouncer_for(neon)


def test_pgbouncer_connections_disable_statement_caching():
    from app.db.session import connect_args

    pooled = "postgresql+asyncpg://u:p@ep-x-pooler.neon.tech/db"
    args = connect_args(make_settings(database_url=pooled), pooled)
    assert args["statement_cache_size"] == 0 and args["prepared_statement_cache_size"] == 0
    assert args["prepared_statement_name_func"]() != args["prepared_statement_name_func"]()
    assert "statement_cache_size" not in connect_args(make_settings(), make_settings().database_url)


def test_production_rejects_wildcard_cors():
    import pytest
    from pydantic import ValidationError

    secret = "x" * 40
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        make_settings(
            app_env="production",
            jwt_secret=secret,
            access_code_secret=secret,
            email_provider="smtp",
            smtp_host="localhost",
            cors_origins="*",
        )


async def test_metrics_label_routes_with_their_full_template(h: Harness):
    """Regression: routes are labelled with the /v1 prefix, so /v1/legal/{doc} (JSON) and
    /legal/{doc} (HTML page) are separate series, and ids never leak into labels."""
    from app.infra import metrics

    await h.client.get("/v1/legal/terms")
    await h.client.get("/legal/terms")
    await h.client.get(f"/v1/listings/{uuid.uuid4()}")
    labels = {s.labels["route"] for m in metrics.REQUESTS.collect() for s in m.samples if "route" in s.labels}
    assert {"/v1/legal/{doc}", "/legal/{doc}", "/v1/listings/{listing_id}"} <= labels
    assert not any(label.count("-") >= 4 for label in labels)  # no raw UUIDs
