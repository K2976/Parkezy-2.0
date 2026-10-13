"""Latency benchmark against a running API.

    uv run python scripts/bench.py --base-url http://localhost:8000 --seed-listings 2000

Seeds a realistic data set straight into the database (hosts, listings with slots, bookings
spread over the next weeks), then fires concurrent requests at the hot endpoints and prints
p50/p95/p99 per endpoint. Seeded rows are tagged and removed with --cleanup.
"""

import argparse
import asyncio
import random
import statistics
import time
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
import httpx
from sqlalchemy.engine import make_url

from app.core.config import get_settings

TAG = "bench-seed"
CENTER = (12.9716, 77.5946)


async def seed(conn: asyncpg.Connection, listings: int) -> None:
    host_id = uuid.uuid4()
    await conn.execute(
        "INSERT INTO users (id, email, full_name, phone, email_verified_at, is_host) VALUES ($1,$2,$3,$4,now(),true)",
        host_id,
        f"{TAG}-{host_id.hex[:8]}@bench.invalid",
        TAG,
        "+919800000000",
    )
    rows, slot_rows = [], []
    for _ in range(listings):
        lid = uuid.uuid4()
        rows.append(
            (
                lid,
                host_id,
                "private",
                "active",
                f"{TAG} spot",
                "1 Bench Road",
                "Bengaluru",
                CENTER[0] + random.uniform(-0.2, 0.2),
                CENTER[1] + random.uniform(-0.2, 0.2),
                "Asia/Kolkata",
                random.choice([30, 40, 50, 60, 80]),
                "INR",
                ["covered"] if random.random() < 0.5 else ["cctv"],
            )
        )
        for n in range(5):
            slot_rows.append((uuid.uuid4(), lid, f"S{n}", "ev" if n == 0 else "standard"))
    await conn.copy_records_to_table(
        "listings",
        records=rows,
        columns=[
            "id",
            "owner_id",
            "kind",
            "status",
            "title",
            "address_line",
            "city",
            "latitude",
            "longitude",
            "timezone",
            "hourly_rate",
            "currency",
            "amenities",
        ],
    )
    await conn.copy_records_to_table("slots", records=slot_rows, columns=["id", "listing_id", "label", "slot_type"])
    driver_id = uuid.uuid4()
    await conn.execute(
        "INSERT INTO users (id, email, full_name, email_verified_at) VALUES ($1,$2,$3,now())",
        driver_id,
        f"{TAG}-{driver_id.hex[:8]}@bench.invalid",
        TAG,
    )
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    bookings = []
    for slot_id, lid, _, _ in random.sample(slot_rows, min(len(slot_rows), listings * 2)):
        start = now + timedelta(hours=random.randint(1, 24 * 14))
        bookings.append(
            (
                uuid.uuid4(),
                driver_id,
                host_id,
                lid,
                slot_id,
                asyncpg.Range(start, start + timedelta(hours=2)),
                "confirmed",
                "pay_at_venue",
                uuid.uuid4().hex,
                "INR",
                40,
                80,
                14.4,
                12,
                94.4,
                0.18,
                0.15,
            )
        )
    await conn.copy_records_to_table(
        "bookings",
        records=bookings,
        columns=[
            "id",
            "driver_id",
            "host_id",
            "listing_id",
            "slot_id",
            "period",
            "status",
            "payment_mode",
            "idempotency_key",
            "currency",
            "hourly_rate",
            "subtotal",
            "tax_amount",
            "platform_fee",
            "total_amount",
            "tax_rate",
            "commission_rate",
        ],
    )
    await conn.execute("ANALYZE listings; ANALYZE slots; ANALYZE bookings;")
    print(f"seeded {listings} listings, {len(slot_rows)} slots, {len(bookings)} bookings")


async def cleanup(conn: asyncpg.Connection) -> None:
    ids = [r["id"] for r in await conn.fetch("SELECT id FROM users WHERE full_name = $1", TAG)]
    await conn.execute("DELETE FROM bookings WHERE driver_id = ANY($1) OR host_id = ANY($1)", ids)
    await conn.execute("DELETE FROM listings WHERE owner_id = ANY($1)", ids)
    await conn.execute("DELETE FROM users WHERE id = ANY($1)", ids)
    print("bench data removed")


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))]


async def measure(client: httpx.AsyncClient, name: str, make_request, total: int, concurrency: int) -> dict:
    latencies: list[float] = []
    errors = 0
    sem = asyncio.Semaphore(concurrency)

    async def one(i: int) -> None:
        nonlocal errors
        async with sem:
            started = time.perf_counter()
            response = await make_request(client, i)
            latencies.append((time.perf_counter() - started) * 1000)
            if response.status_code >= 400 and response.status_code != 409:
                errors += 1

    wall = time.perf_counter()
    await asyncio.gather(*(one(i) for i in range(total)))
    wall = time.perf_counter() - wall
    return {
        "endpoint": name,
        "n": total,
        "p50": statistics.median(latencies),
        "p95": pct(latencies, 95),
        "p99": pct(latencies, 99),
        "rps": total / wall,
        "errors": errors,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--seed-listings", type=int, default=2000)
    parser.add_argument("--requests", type=int, default=400)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    url = make_url(get_settings().database_url)
    conn = await asyncpg.connect(
        user=url.username, password=url.password, host=url.host, port=url.port, database=url.database
    )
    try:
        if args.cleanup:
            await cleanup(conn)
            return
        await seed(conn, args.seed_listings)
        listing_ids = [
            str(r["id"]) for r in await conn.fetch("SELECT id FROM listings WHERE title=$1 LIMIT 200", f"{TAG} spot")
        ]
    finally:
        await conn.close()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:
        email = f"bench-{uuid.uuid4().hex[:8]}@parkezy.dev"
        r = await client.post(
            "/v1/auth/register", json={"email": email, "password": "parking123", "full_name": "Bench"}
        )
        token = r.json()["tokens"]["access_token"]
        authz = {"Authorization": f"Bearer {token}"}
        start = (datetime.now(UTC) + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
        window = {"starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=2)).isoformat()}

        def jitter() -> dict:
            return {
                "latitude": CENTER[0] + random.uniform(-0.1, 0.1),
                "longitude": CENTER[1] + random.uniform(-0.1, 0.1),
            }

        scenarios = [
            ("GET /v1/config", lambda c, i: c.get("/v1/config")),
            (
                "GET /v1/listings (warm cache)",
                lambda c, i: c.get("/v1/listings", params={"latitude": CENTER[0], "longitude": CENTER[1]}),
            ),
            ("GET /v1/listings (cold, 5km)", lambda c, i: c.get("/v1/listings", params=jitter())),
            ("GET /v1/listings (cold, availability)", lambda c, i: c.get("/v1/listings", params=jitter() | window)),
            (
                "GET /v1/listings/{id}",
                lambda c, i: c.get(f"/v1/listings/{listing_ids[i % len(listing_ids)]}", params=window),
            ),
            (
                "POST /v1/bookings/quote",
                lambda c, i: c.post(
                    "/v1/bookings/quote", json={"listing_id": listing_ids[i % len(listing_ids)]} | window
                ),
            ),
            ("GET /v1/me", lambda c, i: c.get("/v1/me", headers=authz)),
            ("GET /v1/bookings", lambda c, i: c.get("/v1/bookings", headers=authz)),
        ]
        results = [await measure(client, name, fn, args.requests, args.concurrency) for name, fn in scenarios]

    print(f"\n{'endpoint':42} {'n':>5} {'p50 ms':>8} {'p95 ms':>8} {'p99 ms':>8} {'req/s':>8} {'err':>4}")
    for r in results:
        latency = f"{r['p50']:>8.1f} {r['p95']:>8.1f} {r['p99']:>8.1f}"
        print(f"{r['endpoint']:42} {r['n']:>5} {latency} {r['rps']:>8.0f} {r['errors']:>4}")


if __name__ == "__main__":
    asyncio.run(main())
