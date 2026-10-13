import asyncio
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.db.models import LedgerEntry
from tests.conftest import Harness
from tests.helpers import auth, book, create_listing, make_host, parse, register, relogin, window


async def _setup(h: Harness, **listing_overrides):
    host = await make_host(h)
    listing = await create_listing(h, host, **listing_overrides)
    driver = await register(h)
    return host, listing, driver


async def test_quote_is_server_computed(h: Harness):
    _, listing, _ = await _setup(h)
    start, end = window(h, hours=2.5)
    r = await h.client.post(
        "/v1/bookings/quote", json={"listing_id": listing["id"], "starts_at": start, "ends_at": end}
    )
    assert r.status_code == 200, r.text
    q = r.json()
    assert (q["subtotal"], q["tax_amount"], q["total"]) == ("100.00", "18.00", "118.00")
    assert q["available"] and not q["requires_approval"] and q["payment_mode"] == "pay_at_venue"
    ev = next(s for s in listing["slots"] if s["label"] == "A2")
    r = await h.client.post(
        "/v1/bookings/quote",
        json={"listing_id": listing["id"], "slot_id": ev["id"], "starts_at": start, "ends_at": end},
    )
    assert r.json()["subtotal"] == "150.00"


async def test_full_lifecycle_pay_at_venue_with_qr_pin_and_overstay(h: Harness):
    host, listing, driver = await _setup(h)
    start, end = window(h, start_in_hours=2, hours=2)  # >= 1h away, so check-in is not open yet
    r = await book(h, driver, listing, start=start, end=end, vehicle_number="ka 01 ab 1234")
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "confirmed" and b["vehicle_number"] == "KA01AB1234"
    assert b["total_amount"] == "94.40" and b["amount_due"] == "94.40"
    assert b["host"]["phone"] and b["driver"]["phone"] is None  # driver sees host phone once confirmed

    await h.drain()
    assert any("Booking confirmed" in e.subject for e in h.email.sent)

    r = await h.client.get(f"/v1/bookings/{b['id']}/access", headers=auth(driver["token"]))
    assert r.status_code == 200, r.text
    creds = r.json()
    assert len(creds["pin"]) == 6

    # Too early: more than 15 minutes before start.
    r = await h.client.post("/v1/host/access/verify", json={"qr_token": creds["qr_token"]}, headers=auth(host["token"]))
    assert r.json()["error"]["code"] == "too_early"

    starts, ends = parse(b["starts_at"]), parse(b["ends_at"])
    h.clock.advance(seconds=(starts - h.clock.now()).total_seconds() - 600)  # 10 minutes before start
    await relogin(h, host, driver)
    creds = (await h.client.get(f"/v1/bookings/{b['id']}/access", headers=auth(driver["token"]))).json()
    stranger = await make_host(h)
    r = await h.client.post(
        "/v1/host/access/verify", json={"qr_token": creds["qr_token"]}, headers=auth(stranger["token"])
    )
    assert r.json()["error"]["code"] == "wrong_host"
    creds = (await h.client.get(f"/v1/bookings/{b['id']}/access", headers=auth(driver["token"]))).json()
    r = await h.client.post("/v1/host/access/verify", json={"qr_token": creds["qr_token"]}, headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    assert r.json()["action"] == "checked_in"
    # Replay of the same QR is refused.
    r = await h.client.post("/v1/host/access/verify", json={"qr_token": creds["qr_token"]}, headers=auth(host["token"]))
    assert r.json()["error"]["code"] == "qr_replayed"

    # Leave 20 minutes late: 5 min grace, then 2 started 15-min blocks = Rs 40 + 18% GST.
    h.clock.advance(seconds=(ends - h.clock.now()).total_seconds() + 20 * 60)
    await relogin(h, host, driver)
    r = await h.client.post(
        "/v1/host/access/verify", json={"listing_id": listing["id"], "pin": "000000"}, headers=auth(host["token"])
    )
    assert r.status_code == 403
    r = await h.client.post(
        "/v1/host/access/verify", json={"listing_id": listing["id"], "pin": creds["pin"]}, headers=auth(host["token"])
    )
    assert r.status_code == 200, r.text
    done = r.json()["booking"]
    assert r.json()["action"] == "checked_out"
    assert done["status"] == "completed"
    assert (done["overstay_minutes"], done["overstay_fee"], done["overstay_tax"]) == (20, "40.00", "7.20")
    assert done["final_amount"] == "141.60" and done["amount_due"] == "0.00"
    assert done["host_earnings"] == "102.00"  # (80 + 40) * 0.85

    async with h.container.session_factory() as s:
        total = await s.scalar(select(func.sum(LedgerEntry.amount)))
        assert total == 0
    r = await h.client.get("/v1/host/dashboard", headers=auth(host["token"]))
    assert Decimal(r.json()["earnings_total"]) == Decimal("102.00")
    assert r.json()["completed_bookings"] == 1

    await h.drain()
    receipt = next(e for e in h.email.sent if e.subject.startswith("Receipt"))
    assert "141.60" in receipt.text and "Overstay" in receipt.text


async def test_cannot_double_book_same_slot_concurrently(h: Harness):
    host, listing, _ = await _setup(h)
    drivers = [await register(h) for _ in range(12)]
    slot = listing["slots"][0]["id"]
    start, end = window(h)
    responses = await asyncio.gather(*[book(h, d, listing, slot_id=slot, start=start, end=end) for d in drivers])
    codes = sorted(r.status_code for r in responses)
    assert codes.count(201) == 1, codes
    assert all(r.json()["error"]["code"] == "slot_unavailable" for r in responses if r.status_code == 409)

    # Overlapping-but-not-identical windows also conflict; adjacent windows are fine.
    later_start = (parse(start) + timedelta(hours=1)).isoformat()
    later_end = (parse(end) + timedelta(hours=1)).isoformat()
    r = await book(h, drivers[0], listing, slot_id=slot, start=later_start, end=later_end)
    assert r.status_code == 409
    r = await book(h, drivers[0], listing, slot_id=slot, start=end, end=later_end)
    assert r.status_code == 201


async def test_auto_pick_assigns_distinct_slots_under_contention(h: Harness):
    _, listing, _ = await _setup(h)
    drivers = [await register(h) for _ in range(5)]
    start, end = window(h)
    responses = await asyncio.gather(*[book(h, d, listing, start=start, end=end) for d in drivers])
    ok = [r.json() for r in responses if r.status_code == 201]
    assert len(ok) == 2
    assert len({b["slot"]["id"] for b in ok}) == 2
    assert all(r.json()["error"]["code"] == "no_availability" for r in responses if r.status_code == 409)


async def test_idempotency_key_replays_instead_of_double_booking(h: Harness):
    _, listing, driver = await _setup(h)
    start, end = window(h)
    key = uuid.uuid4().hex
    first = await book(h, driver, listing, start=start, end=end, key=key)
    again = await book(h, driver, listing, start=start, end=end, key=key)
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    other_end = (parse(end) + timedelta(hours=1)).isoformat()
    mismatch = await book(h, driver, listing, start=start, end=other_end, key=key)
    assert mismatch.json()["error"]["code"] == "idempotency_mismatch"


async def test_booking_guards(h: Harness):
    host, listing, _ = await _setup(h, is_24h=False, open_time="09:00", close_time="18:00")
    unverified = await register(h, verify=False)
    r = await book(h, unverified, listing)
    assert r.json()["error"]["code"] == "email_not_verified"
    r = await book(h, host, listing)
    assert r.json()["error"]["code"] == "own_listing"
    driver = await register(h)
    day = (h.clock.now() + timedelta(days=2)).date()
    night = f"{day}T22:00:00+05:30", f"{day}T23:00:00+05:30"
    r = await book(h, driver, listing, start=night[0], end=night[1])
    assert r.json()["error"]["code"] == "outside_hours"
    r = await book(h, driver, listing, start=f"{day}T10:07:00+05:30", end=f"{day}T11:00:00+05:30")
    assert r.json()["error"]["code"] == "time_not_aligned"
    r = await book(h, driver, listing, start=f"{day}T10:00:00+05:30", end=f"{day}T11:00:00+05:30")
    assert r.status_code == 201


async def test_approval_flow_and_reject(h: Harness):
    host, listing, driver = await _setup(h, auto_accept=False)
    r = await book(h, driver, listing)
    b = r.json()
    assert b["status"] == "pending_approval" and b["approval_expires_at"]
    r = await h.client.get(f"/v1/bookings/{b['id']}/access", headers=auth(driver["token"]))
    assert r.json()["error"]["code"] == "not_confirmed"
    await h.drain()
    assert any(e.subject.startswith("New booking request") for e in h.email.sent)

    r = await h.client.get("/v1/host/bookings", params={"group": "upcoming"}, headers=auth(host["token"]))
    assert [x["id"] for x in r.json()["items"]] == [b["id"]]
    assert r.json()["items"][0]["driver"]["phone"]  # host sees driver's phone

    r = await h.client.post(f"/v1/host/bookings/{b['id']}/approve", headers=auth(driver["token"]))
    assert r.status_code == 403  # driver is not a host
    r = await h.client.post(f"/v1/host/bookings/{b['id']}/approve", headers=auth(host["token"]))
    assert r.json()["status"] == "confirmed"

    second = (await book(h, driver, listing, start=window(h, 6)[0], end=window(h, 6)[1])).json()
    r = await h.client.post(
        f"/v1/host/bookings/{second['id']}/reject", json={"reason": "Driveway blocked"}, headers=auth(host["token"])
    )
    assert r.json()["status"] == "rejected"
    r = await h.client.post(f"/v1/host/bookings/{second['id']}/approve", headers=auth(host["token"]))
    assert r.status_code == 409


async def test_unanswered_requests_and_no_shows_expire(h: Harness):
    from app.workers.jobs import maintenance

    host, listing, driver = await _setup(h, auto_accept=False)
    pending = (await book(h, driver, listing)).json()
    h.clock.advance(minutes=31)
    await relogin(h, host, driver)
    result = await maintenance(h.container)
    assert result["expired"] == 1
    r = await h.client.get(f"/v1/bookings/{pending['id']}", headers=auth(driver["token"]))
    assert r.json()["status"] == "expired"

    await h.client.patch(f"/v1/host/listings/{listing['id']}", json={"auto_accept": True}, headers=auth(host["token"]))
    start, end = window(h, start_in_hours=1, hours=1)
    confirmed = (await book(h, driver, listing, start=start, end=end)).json()
    h.clock.advance(seconds=(parse(confirmed["ends_at"]) - h.clock.now()).total_seconds() - 14 * 60)
    result = await maintenance(h.container)
    assert result["reminders"] == 1
    h.clock.advance(minutes=20)
    await relogin(h, driver)
    result = await maintenance(h.container)
    assert result["no_shows"] == 1
    r = await h.client.get(f"/v1/bookings/{confirmed['id']}", headers=auth(driver["token"]))
    assert r.json()["status"] == "expired"


async def test_cancel_rules_and_list_groups(h: Harness):
    host, listing, driver = await _setup(h)
    b = (await book(h, driver, listing)).json()
    r = await h.client.post(f"/v1/bookings/{b['id']}/cancel", json={}, headers=auth(driver["token"]))
    assert r.status_code == 200 and r.json()["status"] == "cancelled" and r.json()["amount_due"] == "0.00"
    r = await h.client.post(f"/v1/bookings/{b['id']}/cancel", json={}, headers=auth(driver["token"]))
    assert r.status_code == 409

    stranger = await register(h)
    b2 = (await book(h, driver, listing)).json()
    r = await h.client.post(f"/v1/bookings/{b2['id']}/cancel", json={}, headers=auth(stranger["token"]))
    assert r.status_code == 404
    r = await h.client.get(f"/v1/bookings/{b2['id']}", headers=auth(stranger["token"]))
    assert r.status_code == 404

    r = await h.client.get("/v1/bookings", params={"group": "past"}, headers=auth(driver["token"]))
    assert [x["id"] for x in r.json()["items"]] == [b["id"]]
    r = await h.client.get("/v1/bookings", params={"group": "upcoming"}, headers=auth(driver["token"]))
    assert [x["id"] for x in r.json()["items"]] == [b2["id"]]


async def test_pagination_cursor(h: Harness):
    _, listing, driver = await _setup(h)
    ids = []
    for i in range(5):
        start, end = window(h, start_in_hours=2 + 3 * i)
        ids.append((await book(h, driver, listing, start=start, end=end)).json()["id"])
    seen, cursor = [], None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = (await h.client.get("/v1/bookings", params=params, headers=auth(driver["token"]))).json()
        seen += [x["id"] for x in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == list(reversed(ids))
