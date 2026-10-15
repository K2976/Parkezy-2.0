"""Production reliability (loadtest/RESULTS.md, Phase 1): request size limits, NUL rejection,
non-blocking password hashing, bounded database waits with honest 503s, and health checks that
stay truthful and fast while dependencies are down.

Outage scenarios run against throwaway apps whose database/Redis point at a closed port or at a
local TCP server that accepts connections and never answers. Nothing here touches the shared
dev services.
"""

import asyncio
import threading
import time
import uuid
from contextlib import asynccontextmanager

import asyncpg
import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.container import build_container
from app.core.security import PasswordHasher
from app.db import errors as db_errors
from app.main import create_app
from tests.conftest import TEST_URL, FakeEmailSender, FakeJobs, FakePush, FrozenClock, Harness, make_settings
from tests.helpers import auth, book, create_listing, make_host, register, slot_id, window

DEAD = "127.0.0.1:1"  # nothing listens here: connections are refused immediately


def _db_url(hostport: str) -> str:
    host, port = hostport.split(":")
    return make_url(TEST_URL).set(host=host, port=int(port)).render_as_string(hide_password=False)


@asynccontextmanager
async def app_with(container=None, raise_app_exceptions=True, **overrides):
    """A separate app (own settings, and its own container unless one is given)."""
    settings = make_settings(rate_limit_auth_per_window=10_000, rate_limit_default_per_window=10_000, **overrides)
    own = container is None
    if own:
        container = build_container(
            settings,
            jobs=FakeJobs(),
            email_sender=FakeEmailSender(),
            push_sender=FakePush(),
            clock=FrozenClock(),
            payment_gateway=None,
        )
    app = create_app(settings, container)
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions),
                base_url="http://test",
            ) as client,
        ):
            yield client, container
    finally:
        if own:
            await container.aclose()


@asynccontextmanager
async def black_hole():
    """A TCP server that accepts connections and never sends a byte (a frozen database)."""
    writers: list[asyncio.StreamWriter] = []

    async def hold(_reader, writer):
        writers.append(writer)
        await asyncio.Event().wait()

    server = await asyncio.start_server(hold, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield f"127.0.0.1:{port}"
    finally:
        for w in writers:
            w.close()
        server.close()


# ====================================================================== 1. body size limits
async def test_declared_body_over_limit_is_refused_up_front(h: Harness):
    async with app_with(h.container, request_max_body_bytes=2048) as (client, _):
        r = await client.post("/v1/auth/login", content=b"x" * 5000, headers={"Content-Type": "application/json"})
        assert r.status_code == 413, r.text
        assert r.json()["error"]["code"] == "payload_too_large"
        assert r.json()["error"]["details"] == {"max_bytes": 2048}
        # Just under the limit is processed normally (here: a bad login, 401).
        body = b'{"email": "a@test.parkezy.dev", "password": "nope"}' + b" " * 1900  # valid JSON, ~1.9 KB
        r = await client.post("/v1/auth/login", content=body, headers={"Content-Type": "application/json"})
        assert r.status_code == 401, r.text


async def test_streamed_body_without_length_is_cut_off_at_the_limit(h: Harness):
    sent = 0

    async def stream():
        nonlocal sent
        for _ in range(100):
            sent += 1024
            yield b" " * 1024

    async with app_with(h.container, request_max_body_bytes=4096) as (client, _):
        r = await client.post("/v1/auth/login", content=stream(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413, r.text
    assert r.json()["error"]["code"] == "payload_too_large"
    assert sent < 100 * 1024  # stopped reading early, did not buffer the whole stream


async def test_default_limit_rejects_multi_megabyte_bodies(h: Harness):
    assert h.container.settings.request_max_body_bytes == 1024 * 1024
    big = b'{"email": "a@test.parkezy.dev", "password": "' + b"x" * (2 * 1024 * 1024) + b'"}'
    r = await h.client.post("/v1/auth/login", content=big, headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "payload_too_large"


async def test_bodyless_requests_are_unaffected(h: Harness):
    assert (await h.client.get("/v1/config")).status_code == 200
    assert (await h.client.get("/health/live")).status_code == 200


# ====================================================================== 2. NUL characters
async def test_nul_in_json_text_is_400_and_nothing_is_written(h: Harness):
    email = f"nul-{uuid.uuid4().hex[:8]}@test.parkezy.dev"
    body = {"email": email, "password": "parking123", "full_name": "Bad\u0000Name"}
    r = await h.client.post("/v1/auth/register", json=body)
    assert r.status_code == 400, r.text
    err = r.json()["error"]
    assert err["code"] == "invalid_characters"
    assert "full_name" in str(err["details"])
    # The account was not created: the same email registers fine without the NUL.
    r = await h.client.post("/v1/auth/register", json=body | {"full_name": "Good Name"})
    assert r.status_code == 201, r.text


@pytest.mark.parametrize(
    "path_body",
    [
        ("PATCH", "/v1/me", {"full_name": "Nul\u0000Me"}),
        ("POST", "/v1/support", {"category": "other", "subject": "Hello there", "message": "evil \u0000 payload"}),
        ("PUT", "/v1/me/notification-preferences", {"push\u0000": {"bookings": True}}),  # NUL in a key
    ],
)
async def test_nul_rejected_across_endpoints(h: Harness, path_body):
    method, path, body = path_body
    user = await register(h)
    r = await h.client.request(method, path, json=body, headers=auth(user["token"]))
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_characters", r.text


async def test_nul_rejected_in_nested_lists_and_free_form_values(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    r = await h.client.post(
        f"/v1/host/listings/{listing['id']}/slots",
        json=[{"label": "OK1"}, {"label": "B\u0000"}],
        headers=auth(host["token"]),
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_characters", r.text
    slots = (await h.client.get(f"/v1/host/listings/{listing['id']}", headers=auth(host["token"]))).json()["slots"]
    assert "OK1" not in {s["label"] for s in slots}  # the whole request was refused, not half-applied

    admin = await register(h, "admin@test.parkezy.dev")
    r = await h.client.patch(
        "/v1/admin/settings", json={"changes": {"currency": "IN\u0000R"}}, headers=auth(admin["token"])
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_characters", r.text
    assert (await h.client.get("/v1/config")).json()["currency"] == "INR"


@pytest.mark.parametrize("url", ["/v1/admin/users?q=a%00b", "/v1/bookings?cursor=%00", "/v1/listings?q=%2500%00"])
async def test_nul_in_query_string_is_400(h: Harness, url):
    admin = await register(h, "admin@test.parkezy.dev")
    r = await h.client.get(url, headers=auth(admin["token"]))
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_characters", r.text


async def test_nul_in_path_is_400(h: Harness):
    r = await h.client.get("/v1/legal/terms%00")
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_characters", r.text


async def test_ordinary_unicode_still_accepted(h: Harness):
    user = await register(h)
    r = await h.client.patch("/v1/me", json={"full_name": "Ravi 🚗 कुमार"}, headers=auth(user["token"]))
    assert r.status_code == 200 and r.json()["full_name"] == "Ravi 🚗 कुमार"
    # A literal backslash-u sequence typed by a user is text, not a NUL.
    r = await h.client.patch("/v1/me", json={"full_name": "Back\\u0000slash"}, headers=auth(user["token"]))
    assert r.status_code == 200, r.text


# ====================================================================== 3. password hashing
def test_hashing_algorithm_and_parameters_are_unchanged():
    hasher = PasswordHasher()
    a = hasher._argon
    assert (a.time_cost, a.memory_cost, a.parallelism, a.hash_len, a.salt_len) == (3, 65536, 4, 32, 16)
    assert hasher.hash("parking123").startswith("$argon2id$v=19$m=65536,t=3,p=4$")


async def test_async_and_sync_hashes_are_interchangeable():
    hasher = PasswordHasher()
    sync_hash = hasher.hash("parking123")
    assert await hasher.verify_async(sync_hash, "parking123")
    assert not await hasher.verify_async(sync_hash, "wrong")
    assert hasher.verify(await hasher.hash_async("parking123"), "parking123")
    assert not await hasher.verify_async("not-a-hash", "x")


async def test_hashing_does_not_block_the_event_loop():
    hasher = PasswordHasher(max_concurrency=2)
    worst_gap = 0.0
    stop = asyncio.Event()

    async def ticker():
        nonlocal worst_gap
        last = time.perf_counter()
        while not stop.is_set():
            await asyncio.sleep(0.005)
            now = time.perf_counter()
            worst_gap = max(worst_gap, now - last)
            last = now

    tick = asyncio.create_task(ticker())
    started = time.perf_counter()
    await asyncio.gather(*[hasher.hash_async("parking123") for _ in range(6)])
    elapsed = time.perf_counter() - started
    stop.set()
    await tick
    # One argon2 hash is ~70 ms of CPU. Run on the loop, six would freeze it for ~400 ms.
    assert worst_gap < 0.05, f"event loop stalled for {worst_gap * 1000:.0f} ms"
    assert elapsed > 0.05  # sanity: real hashing happened


async def test_hash_concurrency_is_bounded():
    hasher = PasswordHasher(max_concurrency=2)
    active = peak = 0
    lock = threading.Lock()

    def slow_hash(password: str) -> str:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return "hashed"

    hasher.hash = slow_hash  # type: ignore[method-assign]
    assert await asyncio.gather(*[hasher.hash_async("p") for _ in range(10)]) == ["hashed"] * 10
    assert peak == 2


async def test_container_uses_configured_hash_concurrency(h: Harness):
    assert h.container.hasher._max_concurrency == h.container.settings.password_hash_concurrency == 2


async def test_sign_in_flows_still_work_with_async_hashing(h: Harness):
    user = await register(h)  # hash on register
    r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "parking123"})
    assert r.status_code == 200  # verify on login
    r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "wrong-password1"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"
    token = (await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "parking123"})).json()
    r = await h.client.request(
        "DELETE", "/v1/me", json={"password": "nope"}, headers=auth(token["tokens"]["access_token"])
    )
    assert r.status_code == 403  # confirm_password still refuses a wrong password


# ====================================================================== 4. database waits and 503s
async def test_exhausted_pool_answers_503_quickly_without_side_effects(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    async with app_with(db_pool_size=1, db_max_overflow=0, db_pool_timeout_seconds=0.3) as (client, container):
        async with container.engine.connect() as held:  # the only connection is busy
            await held.exec_driver_sql("SELECT 1")
            started = time.perf_counter()
            r = await client.get(f"/v1/listings/{listing['id']}")
            elapsed = time.perf_counter() - started
            assert r.status_code == 503, r.text
            assert r.json()["error"]["code"] == "database_busy"
            assert r.json()["error"]["details"]["reason"] == "pool_exhausted"
            assert r.headers["Retry-After"] == "5"
            assert elapsed < 2.0, elapsed  # bounded by pool_timeout, not the old 30 s

            key = uuid.uuid4().hex
            start, end = window(h)
            body = {"listing_id": listing["id"], "starts_at": start, "ends_at": end}
            r = await client.post("/v1/bookings", json=body, headers=auth(driver["token"]) | {"Idempotency-Key": key})
            assert r.status_code == 503, r.text
        # Pool free again: the failed request left nothing behind, and a retry with the same key books once.
        r = await client.post("/v1/bookings", json=body, headers=auth(driver["token"]) | {"Idempotency-Key": key})
        assert r.status_code == 201, r.text
        mine = (await client.get("/v1/bookings", headers=auth(driver["token"]))).json()["items"]
        assert [b["id"] for b in mine] == [r.json()["id"]]


async def test_unreachable_database_answers_503_fast():
    async with app_with(database_url=_db_url(DEAD)) as (client, _):
        started = time.perf_counter()
        r = await client.get(f"/v1/listings/{uuid.uuid4()}")
        assert r.status_code == 503, r.text
        assert r.json()["error"]["code"] == "database_unavailable"
        assert r.headers["Retry-After"] == "5"
        assert time.perf_counter() - started < 3.0


async def test_hanging_database_is_bounded_by_connect_timeout():
    async with (
        black_hole() as hostport,
        app_with(database_url=_db_url(hostport), db_connect_timeout_seconds=0.5) as (client, _),
    ):
        started = time.perf_counter()
        r = await client.get(f"/v1/listings/{uuid.uuid4()}")
        elapsed = time.perf_counter() - started
    assert r.status_code == 503, r.text
    assert r.json()["error"]["code"] == "database_unavailable"
    assert r.json()["error"]["details"]["reason"] == "connect_timeout"
    assert elapsed < 3.0, elapsed  # asyncpg's own default would wait 60 s


async def test_statement_stuck_on_a_lock_answers_503(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    start, end = window(h)
    quote = {"listing_id": listing["id"], "starts_at": start, "ends_at": end}
    url = make_url(TEST_URL)
    locker = await asyncpg.connect(
        user=url.username, password=url.password, host=url.host, port=url.port, database=url.database
    )
    async with app_with(db_command_timeout_seconds=0.5) as (client, _):
        tx = locker.transaction()
        await tx.start()
        try:
            await locker.execute("LOCK TABLE bookings IN ACCESS EXCLUSIVE MODE")  # e.g. a long migration
            started = time.perf_counter()
            r = await client.post("/v1/bookings/quote", json=quote)
            assert r.status_code == 503, r.text
            assert r.json()["error"]["code"] == "database_busy"
            assert r.json()["error"]["details"]["reason"] == "statement_timeout"
            assert time.perf_counter() - started < 3.0
        finally:
            await tx.rollback()
            await locker.close()
        assert (await client.post("/v1/bookings/quote", json=quote)).status_code == 200


async def test_non_database_errors_are_still_500(h: Harness, monkeypatch):
    from app.services.listing_service import ListingService

    async def boom(self, listing_id):
        raise TimeoutError("an HTTP call timed out, not the database")

    monkeypatch.setattr(ListingService, "get_public", boom)
    # Like uvicorn, don't re-raise the app's exception into the client: we want the response it sent.
    async with app_with(h.container, raise_app_exceptions=False) as (client, _):
        r = await client.get(f"/v1/listings/{uuid.uuid4()}")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"


def test_classifier_leaves_real_sql_errors_alone():
    unique = asyncpg.exceptions.UniqueViolationError("duplicate key")
    assert db_errors.classify(IntegrityError("INSERT", {}, unique)) is None
    assert db_errors.classify(ValueError("bad")) is None
    assert db_errors.classify(asyncpg.exceptions.UndefinedTableError("no such table")) is None
    deadlock = DBAPIError("INSERT", {}, asyncpg.exceptions.DeadlockDetectedError("deadlock detected"))
    assert db_errors.classify(deadlock).code == db_errors.BUSY


# ====================================================================== booking race found while testing
def test_exclusion_deadlock_counts_as_a_lost_slot_race():
    from app.services.booking_service import _lost_slot_race

    try:
        try:
            raise asyncpg.exceptions.DeadlockDetectedError("deadlock detected")
        except asyncpg.exceptions.DeadlockDetectedError as e:
            raise RuntimeError("driver wrapper") from e
    except RuntimeError as wrapped:
        err = DBAPIError("INSERT INTO bookings ...", {}, wrapped)
    assert _lost_slot_race(err)
    other = IntegrityError("INSERT", {}, asyncpg.exceptions.UniqueViolationError("uq_something_else"))
    assert not _lost_slot_race(other)


async def test_concurrent_bookings_never_5xx_and_never_overbook(h: Harness):
    """Overlapping inserts can deadlock inside the exclusion constraint; the loser must see 409 /
    the next free slot, never a server error. Repeated rounds make the deadlock very likely."""
    host = await make_host(h)
    listing = await create_listing(h, host)  # two slots
    drivers = [await register(h) for _ in range(6)]
    for round_ in range(15):
        start, end = window(h, start_in_hours=2 + 3 * round_)
        responses = await asyncio.gather(*[book(h, d, listing, start=start, end=end) for d in drivers])
        codes = sorted(r.status_code for r in responses)
        assert codes == [201, 201, 409, 409, 409, 409], (round_, [r.text for r in responses if r.status_code >= 500])
        assert len({r.json()["slot"]["id"] for r in responses if r.status_code == 201}) == 2

    target = slot_id(listing)
    start, end = window(h, start_in_hours=60)
    responses = await asyncio.gather(*[book(h, d, listing, slot_id=target, start=start, end=end) for d in drivers])
    codes = sorted(r.status_code for r in responses)
    assert codes == [201, 409, 409, 409, 409, 409], [r.text for r in responses]
    assert all(r.json()["error"]["code"] == "slot_unavailable" for r in responses if r.status_code == 409)


# ====================================================================== 5. liveness and readiness
async def test_liveness_answers_instantly_with_every_dependency_down():
    async with (
        black_hole() as hostport,
        app_with(database_url=_db_url(hostport), redis_url=f"redis://{DEAD}/0") as (client, _),
    ):
        started = time.perf_counter()
        r = await client.get("/health/live")
        assert r.status_code == 200 and r.json() == {"status": "ok"}
        assert time.perf_counter() - started < 0.5


async def test_readiness_fails_fast_when_database_hangs():
    async with (
        black_hole() as hostport,
        app_with(database_url=_db_url(hostport), health_check_timeout_seconds=0.5) as (client, _),
    ):
        started = time.perf_counter()
        r = await client.get("/health/ready")
        elapsed = time.perf_counter() - started
    assert r.status_code == 503, r.text
    assert r.json()["status"] == "unavailable"
    assert r.json()["checks"]["database"] == "error: timeout"
    assert elapsed < 1.5, elapsed


async def test_readiness_fails_when_database_refuses():
    async with app_with(database_url=_db_url(DEAD)) as (client, _):
        r = await client.get("/health/ready")
    assert r.status_code == 503 and r.json()["checks"]["database"].startswith("error")


async def test_readiness_stays_up_but_degraded_without_redis():
    async with app_with(redis_url=f"redis://{DEAD}/0") as (client, _):
        r = await client.get("/health/ready")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "degraded"
    assert r.json()["checks"]["database"] == "ok" and r.json()["checks"]["redis"].startswith("error")


async def test_readiness_reports_busy_not_down_when_pool_is_saturated():
    async with (
        app_with(db_pool_size=1, db_max_overflow=0, db_pool_timeout_seconds=5) as (client, container),
        container.engine.connect() as held,
    ):
        await held.exec_driver_sql("SELECT 1")
        started = time.perf_counter()
        r = await client.get("/health/ready")
        assert time.perf_counter() - started < 2.0  # did not wait out the 5 s pool timeout
    assert r.status_code == 200 and r.json()["checks"]["database"] == "busy"


async def test_readiness_healthy_contract_unchanged(h: Harness):
    r = await h.client.get("/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


async def test_metrics_still_scrapeable_during_database_outage():
    async with app_with(database_url=_db_url(DEAD), metrics_token=SecretStr("scrape")) as (client, _):
        await client.get("/health/live")
        r = await client.get("/metrics", headers={"Authorization": "Bearer scrape"})
    assert r.status_code == 200, r.text
    assert "parkezy_outbox_stats_up 0.0" in r.text
    assert "parkezy_outbox_pending" not in r.text  # omitted, not reported as a fake zero
    assert "parkezy_http_requests_total" in r.text


async def test_metrics_reports_outbox_when_database_is_up(h: Harness):
    h.container.settings.metrics_token = SecretStr("scrape")
    try:
        r = await h.client.get("/metrics", headers={"Authorization": "Bearer scrape"})
    finally:
        h.container.settings.metrics_token = None
    assert r.status_code == 200
    assert "parkezy_outbox_stats_up 1.0" in r.text and "parkezy_outbox_pending 0.0" in r.text


async def test_logins_waiting_to_hash_do_not_hold_database_connections(h: Harness):
    """Found in the load test: with hashing off the event loop, logins queued for a hash slot kept
    their pooled connection, so a sign-in burst drained the pool (503 pool_exhausted). A login now
    returns its connection before hashing: 8 concurrent logins share ONE connection and all succeed."""
    users = [await register(h) for _ in range(8)]
    async with app_with(
        db_pool_size=1, db_max_overflow=0, db_pool_timeout_seconds=1.0, password_hash_concurrency=1
    ) as (client, _):
        responses = await asyncio.gather(
            *[client.post("/v1/auth/login", json={"email": u["email"], "password": "parking123"}) for u in users]
        )
    assert [r.status_code for r in responses] == [200] * 8, [r.text for r in responses if r.status_code != 200]


def test_response_models_are_not_scanned_for_nul():
    """The NUL check runs on requests only; building responses (e.g. 200 search results) pays nothing."""
    from app.schemas.listings import ListingSearchItem

    item = ListingSearchItem(
        id=uuid.uuid4(),
        kind="private",
        title="T\u0000",
        address_line="x",
        city="y",
        latitude=1.0,
        longitude=2.0,
        hourly_rate="40",
        currency="INR",
        amenities=[],
        distance_m=1.0,
        total_slots=1,
        available_slots=None,
        cover_photo_url=None,
        rating_avg=None,
    )
    assert item.title == "T\u0000"
