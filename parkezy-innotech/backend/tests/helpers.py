import re
import uuid
from datetime import datetime, timedelta

import httpx

from tests.conftest import Harness

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
BANGALORE = (12.9716, 77.5946)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def code_from_email(h: Harness, to: str) -> str:
    for email in reversed(h.email.sent):
        if email.to == to:
            match = re.search(r"\b(\d{6})\b", email.text)
            assert match, email.text
            return match.group(1)
    raise AssertionError(f"no email to {to}")


async def register(h: Harness, email: str | None = None, *, verify: bool = True, phone: str | None = "+919876543210"):
    email = email or f"user-{uuid.uuid4().hex[:8]}@test.parkezy.dev"
    r = await h.client.post(
        "/v1/auth/register",
        json={"email": email, "password": "parking123", "full_name": "Test User", "phone": phone},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    token = data["tokens"]["access_token"]
    if verify:
        await h.drain()
        code = code_from_email(h, email)
        r = await h.client.post("/v1/auth/verify-email", json={"code": code}, headers=auth(token))
        assert r.status_code == 200, r.text
    return {"email": email, "token": token, "id": data["user"]["id"], "refresh": data["tokens"]["refresh_token"]}


async def make_host(h: Harness, email: str | None = None):
    user = await register(h, email)
    r = await h.client.post("/v1/me/become-host", headers=auth(user["token"]))
    assert r.status_code == 200, r.text
    return user


async def upload_photo(h: Harness, token: str, purpose: str = "listing_photo") -> str:
    r = await h.client.post("/v1/uploads", json={"purpose": purpose, "content_type": "image/png"}, headers=auth(token))
    assert r.status_code == 201, r.text
    data = r.json()
    async with httpx.AsyncClient() as raw:
        put = await raw.put(data["upload_url"], content=PNG, headers=data["headers"])
        assert put.status_code in (200, 204), put.text
    r = await h.client.post(f"/v1/uploads/{data['id']}/complete", headers=auth(token))
    assert r.status_code == 200, r.text
    return data["id"]


async def create_listing(h: Harness, host: dict, **overrides) -> dict:
    photo = await upload_photo(h, host["token"])
    body = {
        "title": "Covered driveway near MG Road",
        "address_line": "12 MG Road",
        "city": "Bengaluru",
        "latitude": BANGALORE[0],
        "longitude": BANGALORE[1],
        "hourly_rate": "40.00",
        "amenities": ["covered", "cctv"],
        "slots": [{"label": "A1"}, {"label": "A2", "slot_type": "ev", "hourly_rate_override": "60.00"}],
        "photo_upload_ids": [photo],
        "auto_accept": True,
    } | overrides
    r = await h.client.post("/v1/host/listings", json=body, headers=auth(host["token"]))
    assert r.status_code == 201, r.text
    return r.json()


def window(h: Harness, start_in_hours: float = 2, hours: float = 2) -> tuple[str, str]:
    now = h.clock.now()
    base = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    start = base + timedelta(hours=start_in_hours - 1)
    return start.isoformat(), (start + timedelta(hours=hours)).isoformat()


async def book(h: Harness, driver: dict, listing: dict, *, slot_id=None, start=None, end=None, key=None, **extra):
    if start is None:
        start, end = window(h)
    body = {"listing_id": listing["id"], "starts_at": start, "ends_at": end} | extra
    if slot_id:
        body["slot_id"] = slot_id
    return await h.client.post(
        "/v1/bookings",
        json=body,
        headers=auth(driver["token"]) | {"Idempotency-Key": key or uuid.uuid4().hex},
    )


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


async def relogin(h: Harness, *users: dict) -> None:
    """Access tokens are short-lived; tests that move the clock forward sign in again."""
    for user in users:
        r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "parking123"})
        assert r.status_code == 200, r.text
        user["token"] = r.json()["tokens"]["access_token"]


def slot_id(listing: dict, label: str = "A1") -> str:
    return next(s["id"] for s in listing["slots"] if s["label"] == label)


async def check_in(h: Harness, host: dict, driver: dict, booking: dict) -> None:
    """Move the clock to the booking start and have the host scan the driver's QR."""
    h.clock.advance(seconds=max(0.0, (parse(booking["starts_at"]) - h.clock.now()).total_seconds()))
    await relogin(h, host, driver)
    creds = (await h.client.get(f"/v1/bookings/{booking['id']}/access", headers=auth(driver["token"]))).json()
    r = await h.client.post("/v1/host/access/verify", json={"qr_token": creds["qr_token"]}, headers=auth(host["token"]))
    assert r.status_code == 200 and r.json()["action"] == "checked_in", r.text


async def complete_booking(h: Harness, host: dict, driver: dict, booking: dict) -> dict:
    """Check in at the start, check out exactly at the end (no overstay). Returns the completed booking."""
    await check_in(h, host, driver, booking)
    h.clock.advance(seconds=max(0.0, (parse(booking["ends_at"]) - h.clock.now()).total_seconds()))
    await relogin(h, host, driver)
    r = await h.client.post(f"/v1/bookings/{booking['id']}/check-out", headers=auth(driver["token"]))
    assert r.status_code == 200 and r.json()["status"] == "completed", r.text
    return r.json()
