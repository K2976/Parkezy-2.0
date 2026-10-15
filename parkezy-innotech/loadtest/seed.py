"""Seed the load-test database and write the k6 fixture file (loadtest/data/users.json).

    cd backend && uv run python ../loadtest/seed.py --drivers 500 --listings 1000

Creates verified drivers (all with the same password), hosts, and listings with slots spread
around central Bengaluru, plus one single-slot "race" listing for the double-booking test.
Writes straight to the database (fast); refuses to touch any database not named *_loadtest.
--reset empties the load-test database first.
"""

import argparse
import asyncio
import json
import os
import random
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "backend"
PASSWORD = "LoadTest123"
CENTER = (12.9716, 77.5946)
SPREAD_DEG = 0.12  # ~13 km either way: most of the city, inside the 25 km search limit


def load_env() -> None:
    """Apply loadtest.env on top of backend/.env before the app reads its settings."""
    for line in (HERE / "loadtest.env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
    os.chdir(BACKEND)  # backend/.env is read relative to the working directory
    sys.path.insert(0, str(BACKEND))


load_env()

import asyncpg  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.security import PasswordHasher  # noqa: E402

TABLES = (
    "receipts, reviews, favorites, payouts, payout_accounts, social_identities, support_tickets, disputes, "
    "notification_preferences, notifications, outbox_events, email_log, ledger_entries, payments, bookings, "
    "listing_media, uploads, slots, listings, push_tokens, verification_codes, refresh_tokens, users"
)


async def main(args: argparse.Namespace) -> None:
    url = make_url(get_settings().database_url)
    if not (url.database or "").endswith("_loadtest"):
        sys.exit(f"Refusing to seed '{url.database}': only databases named *_loadtest are allowed.")
    conn = await asyncpg.connect(
        user=url.username, password=url.password, host=url.host, port=url.port, database=url.database
    )
    try:
        if args.reset:
            await conn.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
            print("emptied the load-test database")
        fixture = await seed(conn, args)
    finally:
        await conn.close()
    out = HERE / "data" / "users.json"
    out.write_text(json.dumps(fixture, indent=1))
    print(f"wrote {out.relative_to(HERE.parent)}: {len(fixture['drivers'])} drivers, {len(fixture['listings'])} listings")


async def seed(conn: asyncpg.Connection, args: argparse.Namespace) -> dict:
    rng = random.Random(args.seed)
    run = uuid.uuid4().hex[:6]  # emails stay unique across repeated seeds without --reset
    password_hash = PasswordHasher().hash(PASSWORD)  # hashing once: argon2 is slow on purpose

    users, hosts, drivers = [], [], []
    for i in range(args.hosts):
        uid = uuid.uuid4()
        email = f"lt-host-{run}-{i}@loadtest.parkezy.dev"
        users.append((uid, email, password_hash, f"Load Host {i}", "+919800000000", True))
        hosts.append({"id": str(uid), "email": email})
    for i in range(args.drivers):
        uid = uuid.uuid4()
        email = f"lt-driver-{run}-{i}@loadtest.parkezy.dev"
        users.append((uid, email, password_hash, f"Load Driver {i}", "+919800000001", False))
        drivers.append(email)
    await conn.executemany(
        "INSERT INTO users (id, email, password_hash, full_name, phone, is_host, email_verified_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, now())",
        users,
    )
    admins = []
    for i in range(args.admins):
        uid, email = uuid.uuid4(), f"lt-admin-{run}-{i}@loadtest.parkezy.dev"
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, full_name, phone, is_host, is_admin, email_verified_at) "
            "VALUES ($1, $2, $3, $4, '+919800000002', true, true, now())",
            uid,
            email,
            password_hash,
            f"Load Admin {i}",
        )
        admins.append(email)

    listings, slots, listing_ids = [], [], []
    amenity_pool = ["covered", "cctv", "gated", "well_lit", "ev_charging", "security_guard"]
    for i in range(args.listings):
        lid = uuid.uuid4()
        host = hosts[i % len(hosts)]
        listings.append(
            (
                lid,
                uuid.UUID(host["id"]),
                "private",
                "active",
                f"Load test spot {i}",
                f"{i} Test Road",
                "Bengaluru",
                CENTER[0] + rng.uniform(-SPREAD_DEG, SPREAD_DEG),
                CENTER[1] + rng.uniform(-SPREAD_DEG, SPREAD_DEG),
                "Asia/Kolkata",
                rng.sample(amenity_pool, rng.randint(1, 3)),
                rng.choice([30, 40, 50, 60, 80]),
                "INR",
                rng.random() > args.manual_share,  # auto_accept
                True,
                [1, 2, 3, 4, 5, 6, 7],
            )
        )
        listing_ids.append(str(lid))
        for n in range(args.slots):
            slots.append((uuid.uuid4(), lid, f"S{n}", "ev" if n == 0 else "standard", True))

    race_id, race_slot = uuid.uuid4(), uuid.uuid4()
    listings.append(
        (
            race_id,
            uuid.UUID(hosts[0]["id"]),
            "private",
            "active",
            "Load test RACE spot (single slot)",
            "1 Contention Lane",
            "Bengaluru",
            CENTER[0],
            CENTER[1],
            "Asia/Kolkata",
            ["covered"],
            40,
            "INR",
            True,
            True,
            [1, 2, 3, 4, 5, 6, 7],
        )
    )
    slots.append((race_slot, race_id, "R1", "standard", True))

    await conn.copy_records_to_table(
        "listings",
        records=listings,
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
            "amenities",
            "hourly_rate",
            "currency",
            "auto_accept",
            "is_24h",
            "open_days",
        ],
    )
    await conn.copy_records_to_table(
        "slots", records=slots, columns=["id", "listing_id", "label", "slot_type", "is_active"]
    )
    return {
        "password": PASSWORD,
        "center": list(CENTER),
        "drivers": drivers,
        "hosts": hosts,
        "admins": admins,
        "listings": listing_ids,
        "race_listing": {"id": str(race_id), "slot_id": str(race_slot)},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--drivers", type=int, default=500)
    parser.add_argument("--hosts", type=int, default=50)
    parser.add_argument("--admins", type=int, default=5)
    parser.add_argument("--listings", type=int, default=1000)
    parser.add_argument("--slots", type=int, default=4, help="slots per listing")
    parser.add_argument("--manual-share", type=float, default=0.2, help="share of listings needing host approval")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--reset", action="store_true", help="empty the load-test database first")
    asyncio.run(main(parser.parse_args()))
