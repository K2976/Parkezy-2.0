"""Integration test harness: a real PostgreSQL+PostGIS database, real Redis and the local
S3 store from docker compose. External SaaS (email, push, payments) is replaced by fakes
that implement the same ports, so no test ever reaches the internet.

The test database is created fresh (`<db>_test`) and migrated with Alembic every run.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import asyncpg
import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

os.environ.setdefault("APP_ENV", "test")
os.environ["EMAIL_PROVIDER"] = "console"
os.environ["PAYMENT_PROVIDER"] = "offline"
os.environ["PUSH_PROVIDER"] = "none"
os.environ["CORS_ORIGINS"] = ""
os.environ["ADMIN_EMAILS"] = "admin@test.parkezy.dev"

from app.core.config import Settings  # noqa: E402

BASE = Settings()  # type: ignore[call-arg]
TEST_DB = f"{make_url(BASE.database_url).database}_test"
TEST_URL = make_url(BASE.database_url).set(database=TEST_DB).render_as_string(hide_password=False)
os.environ["DATABASE_URL"] = TEST_URL
os.environ["REDIS_URL"] = BASE.redis_url.rsplit("/", 1)[0] + "/15"
os.environ["S3_BUCKET"] = f"{BASE.s3_bucket}-test"


def make_settings(**overrides) -> Settings:
    return Settings(**overrides)  # type: ignore[call-arg]


# ---------------------------------------------------------------- fakes
class FakeJobs:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def enqueue(self, task: str, *args: object, countdown_seconds: int | None = None) -> None:
        self.calls.append((task, args))


@dataclass
class FakeEmailSender:
    sent: list = field(default_factory=list)
    fail: bool = False

    async def send(self, email) -> str:
        from app.core.errors import ExternalServiceError

        if self.fail:
            raise ExternalServiceError("boom")
        self.sent.append(email)
        return f"msg-{len(self.sent)}"


@dataclass
class FakePush:
    sent: list = field(default_factory=list)

    async def send(self, message) -> list[str]:
        self.sent.append(message)
        return []


class FakeGateway:
    name = "razorpay"
    public_key = "rzp_test_key"

    def __init__(self) -> None:
        self.orders: list = []
        self.refunds: list = []

    async def create_order(self, *, amount, currency, receipt, notes):
        from app.integrations.payments import GatewayOrder, to_minor_units

        order = GatewayOrder(
            "razorpay", f"order_{uuid.uuid4().hex[:12]}", to_minor_units(amount), currency, self.public_key
        )
        self.orders.append(order)
        return order

    def verify_checkout_signature(self, *, order_id, payment_id, signature) -> bool:
        return signature == f"sig:{order_id}:{payment_id}"

    def verify_webhook_signature(self, *, body, signature) -> bool:
        return signature == "good"

    async def refund(self, *, payment_id, amount: Decimal) -> str:
        self.refunds.append((payment_id, amount))
        return f"rfnd_{len(self.refunds)}"


class FrozenClock:
    """Time stands still unless a test moves it, so durations are exact."""

    def __init__(self) -> None:
        self.current = datetime.now(UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs) -> None:
        self.current += timedelta(**kwargs)


# ---------------------------------------------------------------- database
async def _recreate_database() -> None:
    admin = make_url(BASE.database_url)
    conn = await asyncpg.connect(
        user=admin.username, password=admin.password, host=admin.host, port=admin.port, database=admin.database
    )
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await conn.close()


def _migrate() -> None:
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    cfg.attributes["database_url"] = TEST_URL
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
async def database() -> AsyncIterator[None]:
    await _recreate_database()
    await asyncio.to_thread(_migrate)
    yield


TRUNCATE = (
    "TRUNCATE users, refresh_tokens, verification_codes, push_tokens, listings, slots, uploads, listing_media, "
    "bookings, payments, ledger_entries, notifications, outbox_events, email_log, email_suppressions, "
    "webhook_events, disputes, notification_preferences, support_tickets RESTART IDENTITY CASCADE"
)


@dataclass
class Harness:
    client: httpx.AsyncClient
    container: object
    jobs: FakeJobs
    email: FakeEmailSender
    push: FakePush
    clock: FrozenClock
    gateway: FakeGateway | None

    async def drain(self) -> int:
        from app.workers.jobs import process_outbox

        return await process_outbox(self.container)


async def _harness(online_payments: bool) -> AsyncIterator[Harness]:
    from sqlalchemy import text

    from app.container import build_container
    from app.main import create_app

    # Many users share one test client IP; rate limiting has its own dedicated test.
    settings = make_settings(rate_limit_auth_per_window=10_000, rate_limit_default_per_window=10_000)
    jobs, email, push, clock = FakeJobs(), FakeEmailSender(), FakePush(), FrozenClock()
    gateway = FakeGateway() if online_payments else None
    container = build_container(
        settings, jobs=jobs, email_sender=email, push_sender=push, clock=clock, payment_gateway=gateway
    )
    async with container.engine.begin() as conn:
        await conn.execute(text(TRUNCATE))
        # Restore business rules to the migration seed in case a previous test changed them.
        await conn.execute(text("CREATE TABLE IF NOT EXISTS _seed_settings AS TABLE platform_settings"))
        await conn.execute(text("DELETE FROM platform_settings"))
        await conn.execute(text("INSERT INTO platform_settings SELECT * FROM _seed_settings"))
    await container.redis.flushdb()
    app = create_app(settings, container)
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        yield Harness(client, container, jobs, email, push, clock, gateway)
    await container.aclose()


@pytest.fixture
async def h() -> AsyncIterator[Harness]:
    async for harness in _harness(online_payments=False):
        yield harness


@pytest.fixture
async def hp() -> AsyncIterator[Harness]:
    """Harness with online payments (fake Razorpay gateway)."""
    async for harness in _harness(online_payments=True):
        yield harness
