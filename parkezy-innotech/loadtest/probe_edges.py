"""Hostile and malformed input probe: things real clients (and attackers) send.

    cd backend && uv run python ../loadtest/probe_edges.py

Every case states the acceptable answers. The server must never return 5xx for bad INPUT,
never hang, and never accept something it should refuse. Uses the load-test API (8001, raised
rate limits) for input cases and the dev API (8000, real limits) for brute-force cases.
"""

import asyncio
import base64
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx

LT = os.environ.get("LT_URL", "http://localhost:8001")
DEV = os.environ.get("DEV_URL", "http://localhost:8000")
FIXTURE = json.loads(open(os.path.join(os.path.dirname(__file__), "data", "users.json")).read())
PASSWORD = FIXTURE["password"]
results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


async def expect(c: httpx.AsyncClient, name: str, method: str, url: str, ok: set[int], **kw) -> httpx.Response | None:
    started = time.perf_counter()
    try:
        r = await c.request(method, url, timeout=30, **kw)
    except (httpx.HTTPError, httpx.InvalidURL) as e:
        record(name, False, f"transport error {type(e).__name__}: {e}")
        return None
    ms = (time.perf_counter() - started) * 1000
    good = r.status_code in ok
    detail = f"{r.status_code} in {ms:.0f} ms"
    if not good:
        detail += f" (expected {sorted(ok)}) body={r.text[:200]!r}"
    record(name, good, detail)
    return r


async def token(c: httpx.AsyncClient, email: str) -> str:
    r = await c.post(f"{LT}/v1/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["tokens"]["access_token"]


def window(hours_ahead: float = 3, hours: float = 1) -> dict:
    step = 15 * 60
    start = datetime.fromtimestamp((int(time.time() + hours_ahead * 3600) // step + 1) * step, UTC)
    return {"starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=hours)).isoformat()}


async def main() -> None:
    async with httpx.AsyncClient() as c:
        D = await token(c, FIXTURE["drivers"][0])
        H = await token(c, FIXTURE["hosts"][0]["email"])
        auth = {"Authorization": f"Bearer {D}"}
        hauth = {"Authorization": f"Bearer {H}"}
        listing = FIXTURE["listings"][0]
        bad_input = {400, 401, 403, 404, 409, 413, 415, 422}

        # ---------------------------------------------------------------- body shape / size
        await expect(c, "invalid JSON body", "POST", f"{LT}/v1/auth/login", {422},
                     content=b"{not json", headers={"Content-Type": "application/json"})
        await expect(c, "JSON body sent as text/plain", "POST", f"{LT}/v1/auth/login", {422},
                     content=json.dumps({"email": "a@b.co", "password": "x"}), headers={"Content-Type": "text/plain"})
        await expect(c, "empty body on POST /v1/bookings", "POST", f"{LT}/v1/bookings", {422},
                     headers=auth | {"Idempotency-Key": uuid.uuid4().hex})
        deep = "[" * 100_000 + "]" * 100_000
        await expect(c, "100k-deep nested JSON", "POST", f"{LT}/v1/auth/login", bad_input,
                     content=deep, headers={"Content-Type": "application/json"})
        big = json.dumps({"email": "a@b.co", "password": "x" * 20_000_000})
        await expect(c, "20 MB JSON body (login)", "POST", f"{LT}/v1/auth/login", bad_input,
                     content=big, headers={"Content-Type": "application/json"})
        many_keys = json.dumps({f"k{i}": i for i in range(500_000)})
        await expect(c, "500k-key JSON object", "PATCH", f"{LT}/v1/me", bad_input | {200},
                     content=many_keys, headers=auth | {"Content-Type": "application/json"})

        # ---------------------------------------------------------------- strings the DB can't store
        await expect(c, "NUL byte in full_name (register)", "POST", f"{LT}/v1/auth/register", {201} | bad_input,
                     json={"email": f"nul-{uuid.uuid4().hex[:8]}@loadtest.parkezy.dev", "password": "Abcdef123",
                           "full_name": "Bad\u0000Name"})
        await expect(c, "NUL byte in support message", "POST", f"{LT}/v1/support", {201} | bad_input,
                     json={"category": "other", "subject": "Hello there", "message": "evil \u0000 payload here"},
                     headers=auth)
        await expect(c, "NUL byte in profile name", "PATCH", f"{LT}/v1/me", {200} | bad_input,
                     json={"full_name": "Nul\u0000Me"}, headers=auth)
        await expect(c, "NUL byte in admin search q", "GET", f"{LT}/v1/admin/users", bad_input | {200},
                     params={"q": "a\u0000b"}, headers=auth)
        await expect(c, "lone surrogate in name", "PATCH", f"{LT}/v1/me", {200} | bad_input,
                     content='{"full_name": "x\\ud800y"}', headers=auth | {"Content-Type": "application/json"})
        await expect(c, "emoji + RTL name", "PATCH", f"{LT}/v1/me", {200},
                     json={"full_name": "Ravi 🚗 ‮Kumar"}, headers=auth)

        # ---------------------------------------------------------------- numbers and dates
        for name, params in {
            "search NaN latitude": {"latitude": "NaN", "longitude": 77.59},
            "search inf longitude": {"latitude": 12.9, "longitude": "inf"},
            "search 1e308 radius": {"latitude": 12.9, "longitude": 77.59, "radius_km": "1e308"},
            "search negative radius": {"latitude": 12.9, "longitude": 77.59, "radius_km": -5},
            "search limit 10^18": {"latitude": 12.9, "longitude": 77.59, "limit": 10**18},
            "search 1000 amenities": {"latitude": 12.9, "longitude": 77.59, "amenities": ["covered"] * 1000},
        }.items():
            await expect(c, name, "GET", f"{LT}/v1/listings", bad_input | {200}, params=params)
        await expect(c, "bookings limit 10^30", "GET", f"{LT}/v1/bookings", bad_input | {200},
                     params={"limit": 10**30}, headers=auth)
        cursor = base64.urlsafe_b64encode(f"9999-12-31T23:59:59+00:00|{uuid.uuid4()}".encode()).decode()
        await expect(c, "cursor at year 9999", "GET", f"{LT}/v1/bookings", {200}, params={"cursor": cursor}, headers=auth)
        await expect(c, "cursor garbage", "GET", f"{LT}/v1/bookings", {422}, params={"cursor": "%%%"}, headers=auth)
        for name, w in {
            "booking year 9999": {"starts_at": "9999-12-31T10:00:00+00:00", "ends_at": "9999-12-31T11:00:00+00:00"},
            "booking year 0001": {"starts_at": "0001-01-01T10:00:00+00:00", "ends_at": "0001-01-01T11:00:00+00:00"},
            "booking invalid date": {"starts_at": "2026-13-45T10:00:00+00:00", "ends_at": "2026-13-45T11:00:00+00:00"},
            "booking +14:00 offset": {"starts_at": "2027-01-01T10:00:00+14:00", "ends_at": "2027-01-01T11:00:00+14:00"},
            "booking ends before start": {"starts_at": window()["ends_at"], "ends_at": window()["starts_at"]},
        }.items():
            await expect(c, name, "POST", f"{LT}/v1/bookings", bad_input, json={"listing_id": listing, **w},
                         headers=auth | {"Idempotency-Key": uuid.uuid4().hex})
        await expect(c, "quote with huge daily window (7 days)", "POST", f"{LT}/v1/bookings/quote", {200} | bad_input,
                     json={"listing_id": listing, **window(3, 24 * 7)})
        await expect(c, "listing hourly_rate 1e12", "POST", f"{LT}/v1/host/listings", bad_input,
                     json={"title": "Huge price", "address_line": "x", "city": "Pune", "latitude": 18.5,
                           "longitude": 73.8, "hourly_rate": "1000000000000", "slots": [{"label": "1"}],
                           "publish": False}, headers=hauth)
        await expect(c, "listing 10,000 slots", "POST", f"{LT}/v1/host/listings", bad_input | {201},
                     json={"title": "Many slots", "address_line": "x", "city": "Pune", "latitude": 18.5,
                           "longitude": 73.8, "hourly_rate": "30", "slots": [{"label": str(i)} for i in range(10_000)],
                           "publish": False}, headers=hauth)
        await expect(c, "Idempotency-Key 5 KB", "POST", f"{LT}/v1/bookings", bad_input,
                     json={"listing_id": listing, **window()}, headers=auth | {"Idempotency-Key": "k" * 5000})

        # ---------------------------------------------------------------- ids and paths
        await expect(c, "non-UUID booking id", "GET", f"{LT}/v1/bookings/not-a-uuid", {422}, headers=auth)
        await expect(c, "path traversal in legal doc", "GET", f"{LT}/v1/legal/..%2F..%2Fetc%2Fpasswd", {404, 422})
        await expect(c, "SQL-ish admin search", "GET", f"{LT}/v1/admin/users", {403}, params={"q": "' OR 1=1 --"},
                     headers=auth)
        await expect(c, "unknown route", "GET", f"{LT}/v1/does-not-exist", {404})
        await expect(c, "wrong method", "DELETE", f"{LT}/v1/config", {405})

        # ---------------------------------------------------------------- tokens
        header, payload, _sig = D.split(".")
        none_alg = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        for name, tok in {
            "JWT alg=none": f"{none_alg}.{payload}.",
            "JWT tampered payload": f"{header}.{payload[:-2]}AA.{_sig}",
            "JWT random string": "abc.def.ghi",
            "JWT empty": "",
            "JWT 100 KB": "a" * 100_000,
        }.items():
            await expect(c, name, "GET", f"{LT}/v1/me", {401, 403, 431}, headers={"Authorization": f"Bearer {tok}"})
        await expect(c, "refresh token 10 KB", "POST", f"{LT}/v1/auth/refresh", {401, 422}, json={"refresh_token": "r" * 10_000})

        # ---------------------------------------------------------------- races that must not 500
        email = f"race-{uuid.uuid4().hex[:8]}@loadtest.parkezy.dev"
        body = {"email": email, "password": "Abcdef123", "full_name": "Race"}
        rs = await asyncio.gather(*[c.post(f"{LT}/v1/auth/register", json=body, timeout=30) for _ in range(20)])
        codes = sorted(r.status_code for r in rs)
        record("20 parallel sign-ups with one email", codes.count(201) == 1 and set(codes) <= {201, 409}, str(codes))
        key = uuid.uuid4().hex
        b = {"listing_id": FIXTURE["listings"][1], **window(5)}
        rs = await asyncio.gather(*[c.post(f"{LT}/v1/bookings", json=b, headers=auth | {"Idempotency-Key": key}, timeout=30)
                                    for _ in range(20)])
        codes = sorted(r.status_code for r in rs)
        ids = {r.json().get("id") for r in rs if r.status_code in (200, 201)}
        record("20 parallel retries of one booking (same Idempotency-Key)",
               codes.count(201) == 1 and set(codes) <= {200, 201} and len(ids) == 1, f"{codes}, distinct bookings={len(ids)}")

        # ---------------------------------------------------------------- real rate limits (dev API, 8000)
        try:
            await c.get(f"{DEV}/health/live", timeout=3)
            dev_up = True
        except httpx.HTTPError:
            dev_up = False
        if dev_up:
            victim = f"bruteforce-{uuid.uuid4().hex[:6]}@example.com"
            codes = [(await c.post(f"{DEV}/v1/auth/login", json={"email": victim, "password": f"guess{i}"})).status_code
                     for i in range(15)]
            record("15 password guesses on the real API", 429 in codes and codes.index(429) <= 10, str(codes))
            r = await c.post(f"{DEV}/v1/auth/login", json={"email": victim, "password": "x"})
            record("429 carries Retry-After", r.status_code != 429 or "retry-after" in r.headers,
                   f"{r.status_code} retry-after={r.headers.get('retry-after')}")
        else:
            record("rate limits on the real API", False, "dev API on :8000 not running; skipped")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    for name, _, detail in failed:
        print(f"  FAIL {name}: {detail}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
