"""Extend a booking.

Contract
--------
POST /v1/bookings/{booking_id}/extend/quote   body {ends_at}  -> 200 ExtensionQuote
POST /v1/bookings/{booking_id}/extend         body {ends_at}  -> 200 BookingOut

ExtensionQuote = {booking_id, current_ends_at, new_ends_at, additional_minutes,
                  subtotal, tax_amount, total, currency, available}

Rules
-----
* Driver only. Host, strangers and unknown ids get 404; no token -> 401.
* Status must be `confirmed` or `checked_in`; anything else -> 409 `not_extendable`.
* Not after the current end (overstaying drivers pay overstay instead) -> 409 `booking_ended`.
* `ends_at` == current end is an idempotent no-op (200, unchanged) so client retries are safe;
  `ends_at` earlier than the current end -> 422 `invalid_extension`.
* Same validation as booking: timezone required (`naive_datetime`), step-aligned (`time_not_aligned`),
  total duration <= max_booking_minutes (`duration_out_of_range`), opening hours (`outside_hours`).
* The same slot must stay free for the extra time -> 409 `slot_unavailable` (never moves slots).
  The quote reports `available: false` instead of failing.
* Extra time is priced at the booking's locked `hourly_rate` (host rate changes after booking
  do not apply) plus GST; booking subtotal/tax/total/amount_due grow by the extension.
* Online payment mode: booking stays confirmed, `amount_due` grows and POST /payment opens an order
  for just the outstanding amount.
* Checking out before the new end is not an overstay.
"""

import asyncio
import uuid
from datetime import timedelta
from decimal import Decimal

from tests.conftest import Harness
from tests.helpers import (
    auth,
    book,
    check_in,
    create_listing,
    make_host,
    parse,
    register,
    relogin,
    slot_id,
    window,
)


def _plus(ts: str, **delta) -> str:
    return (parse(ts) + timedelta(**delta)).isoformat()


async def _setup(h: Harness, **listing_overrides):
    host = await make_host(h)
    listing = await create_listing(h, host, **listing_overrides)
    driver = await register(h)
    b = (await book(h, driver, listing, slot_id=slot_id(listing))).json()  # A1 @ 40/h, 2 h
    assert b["total_amount"] == "94.40", b
    return host, listing, driver, b


async def _extend(h: Harness, user: dict, booking_id: str, ends_at: str, *, quote: bool = False):
    path = f"/v1/bookings/{booking_id}/extend" + ("/quote" if quote else "")
    return await h.client.post(path, json={"ends_at": ends_at}, headers=auth(user["token"]))


async def test_quote_and_extend_by_one_hour(h: Harness):
    host, _, driver, b = await _setup(h)
    new_end = _plus(b["ends_at"], hours=1)
    r = await _extend(h, driver, b["id"], new_end, quote=True)
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["additional_minutes"] == 60 and q["available"] is True
    assert (q["subtotal"], q["tax_amount"], q["total"]) == ("40.00", "7.20", "47.20")
    assert parse(q["new_ends_at"]) == parse(new_end) and parse(q["current_ends_at"]) == parse(b["ends_at"])

    # A quote changes nothing.
    same = (await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()
    assert same["ends_at"] == b["ends_at"]

    r = await _extend(h, driver, b["id"], new_end)
    assert r.status_code == 200, r.text
    e = r.json()
    assert parse(e["ends_at"]) == parse(new_end) and e["status"] == "confirmed"
    assert (e["subtotal"], e["tax_amount"], e["total_amount"]) == ("120.00", "21.60", "141.60")
    assert e["amount_due"] == "141.60"
    assert e["slot"]["id"] == b["slot"]["id"]

    # The host sees the new end time too.
    r = await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(host["token"]))
    assert parse(r.json()["ends_at"]) == parse(new_end)


async def test_repeating_the_same_extension_is_a_no_op(h: Harness):
    _, _, driver, b = await _setup(h)
    new_end = _plus(b["ends_at"], hours=1)
    first = (await _extend(h, driver, b["id"], new_end)).json()
    r = await _extend(h, driver, b["id"], new_end)  # client retry after a timeout
    assert r.status_code == 200, r.text
    assert r.json()["total_amount"] == first["total_amount"] == "141.60"


async def test_extension_validation(h: Harness):
    _, _, driver, b = await _setup(h)
    cases = {
        "invalid_extension": _plus(b["ends_at"], minutes=-15),
        "time_not_aligned": _plus(b["ends_at"], minutes=7),
        "duration_out_of_range": _plus(b["starts_at"], days=7, minutes=15),  # > 10080 min total
    }
    for code, ends_at in cases.items():
        r = await _extend(h, driver, b["id"], ends_at)
        assert r.status_code == 422 and r.json()["error"]["code"] == code, (code, r.text)
        r = await _extend(h, driver, b["id"], ends_at, quote=True)
        assert r.status_code == 422 and r.json()["error"]["code"] == code, (code, r.text)

    naive = parse(b["ends_at"]).replace(tzinfo=None) + timedelta(hours=1)
    r = await _extend(h, driver, b["id"], naive.isoformat())
    assert r.status_code == 422 and r.json()["error"]["code"] == "naive_datetime", r.text
    r = await h.client.post(f"/v1/bookings/{b['id']}/extend", json={}, headers=auth(driver["token"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_failed"

    # Exactly the max total duration is allowed.
    r = await _extend(h, driver, b["id"], _plus(b["starts_at"], days=7))
    assert r.status_code == 200, r.text

    unchanged = (await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()
    assert parse(unchanged["ends_at"]) == parse(b["starts_at"]) + timedelta(days=7)


async def test_extension_respects_opening_hours(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host, is_24h=False, open_time="09:00", close_time="18:00")
    driver = await register(h)
    day = (h.clock.now() + timedelta(days=2)).date()
    start, end = f"{day}T16:00:00+05:30", f"{day}T17:00:00+05:30"
    b = (await book(h, driver, listing, slot_id=slot_id(listing), start=start, end=end)).json()
    r = await _extend(h, driver, b["id"], f"{day}T18:30:00+05:30")
    assert r.status_code == 422 and r.json()["error"]["code"] == "outside_hours", r.text
    r = await _extend(h, driver, b["id"], f"{day}T18:00:00+05:30")  # closing time exactly is fine
    assert r.status_code == 200, r.text


async def test_cannot_extend_into_someone_elses_booking(h: Harness):
    _, listing, driver, b = await _setup(h)
    other = await register(h)
    nxt = await book(h, other, listing, slot_id=b["slot"]["id"], start=b["ends_at"], end=_plus(b["ends_at"], hours=1))
    assert nxt.status_code == 201, nxt.text

    q = (await _extend(h, driver, b["id"], _plus(b["ends_at"], minutes=30), quote=True)).json()
    assert q["available"] is False
    r = await _extend(h, driver, b["id"], _plus(b["ends_at"], minutes=30))
    assert r.status_code == 409 and r.json()["error"]["code"] == "slot_unavailable", r.text
    # Even though slot A2 is free, the driver is never moved to another slot.
    after = (await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()
    assert after["ends_at"] == b["ends_at"] and after["slot"]["id"] == b["slot"]["id"]

    # Once the other booking is cancelled, the same extension succeeds.
    await h.client.post(f"/v1/bookings/{nxt.json()['id']}/cancel", json={}, headers=auth(other["token"]))
    assert (await _extend(h, driver, b["id"], _plus(b["ends_at"], minutes=30))).status_code == 200


async def test_extension_racing_a_new_booking_has_one_winner(h: Harness):
    _, listing, driver, b = await _setup(h)
    rival = await register(h)
    new_end = _plus(b["ends_at"], hours=1)
    ext, rival_booking = await asyncio.gather(
        _extend(h, driver, b["id"], new_end),
        book(h, rival, listing, slot_id=b["slot"]["id"], start=b["ends_at"], end=new_end),
    )
    assert sorted([ext.status_code, rival_booking.status_code]) in ([200, 409], [201, 409]), (
        ext.text,
        rival_booking.text,
    )


async def test_concurrent_extensions_stay_consistent(h: Harness):
    _, _, driver, b = await _setup(h)
    targets = [_plus(b["ends_at"], hours=n) for n in (1, 2, 3)]
    responses = await asyncio.gather(*[_extend(h, driver, b["id"], t) for t in targets])
    assert any(r.status_code == 200 for r in responses), [r.text for r in responses]
    final = (await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()
    assert parse(final["ends_at"]) > parse(b["ends_at"])
    hours = Decimal((parse(final["ends_at"]) - parse(final["starts_at"])).total_seconds() / 3600)
    # Whatever order they landed in, the price matches the stored duration exactly.
    assert Decimal(final["subtotal"]) == hours * 40
    assert Decimal(final["tax_amount"]) == (hours * 40 * Decimal("0.18")).quantize(Decimal("0.01"))


async def test_extension_uses_the_rate_locked_at_booking(h: Harness):
    host, listing, driver, b = await _setup(h)
    r = await h.client.patch(
        f"/v1/host/listings/{listing['id']}", json={"hourly_rate": "100.00"}, headers=auth(host["token"])
    )
    assert r.status_code == 200
    q = (await _extend(h, driver, b["id"], _plus(b["ends_at"], hours=1), quote=True)).json()
    assert q["subtotal"] == "40.00", q


async def test_checked_in_driver_extends_and_leaves_without_overstay(h: Harness):
    host, _, driver, b = await _setup(h)
    await check_in(h, host, driver, b)
    r = await _extend(h, driver, b["id"], _plus(b["ends_at"], hours=1))
    assert r.status_code == 200 and r.json()["status"] == "checked_in", r.text

    # Leave 30 minutes after the ORIGINAL end: inside the extended time, so no overstay.
    h.clock.advance(seconds=(parse(b["ends_at"]) - h.clock.now()).total_seconds() + 30 * 60)
    await relogin(h, driver)
    r = await h.client.post(f"/v1/bookings/{b['id']}/check-out", headers=auth(driver["token"]))
    assert r.status_code == 200, r.text
    done = r.json()
    assert (done["overstay_minutes"], done["overstay_fee"]) == (0, "0.00")
    assert done["final_amount"] == "141.60"


async def test_cannot_extend_after_the_booking_has_ended(h: Harness):
    host, _, driver, b = await _setup(h)
    await check_in(h, host, driver, b)
    h.clock.advance(seconds=(parse(b["ends_at"]) - h.clock.now()).total_seconds() + 60)
    await relogin(h, driver)
    r = await _extend(h, driver, b["id"], _plus(b["ends_at"], hours=1))
    assert r.status_code == 409 and r.json()["error"]["code"] == "booking_ended", r.text


async def test_only_confirmed_or_checked_in_bookings_extend(h: Harness):
    host = await make_host(h)
    manual = await create_listing(h, host, auto_accept=False)
    driver = await register(h)
    pending = (await book(h, driver, manual)).json()
    assert pending["status"] == "pending_approval"
    r = await _extend(h, driver, pending["id"], _plus(pending["ends_at"], hours=1))
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_extendable", r.text

    listing = await create_listing(h, host, title="Instant")
    cancelled = (await book(h, driver, listing)).json()
    await h.client.post(f"/v1/bookings/{cancelled['id']}/cancel", json={}, headers=auth(driver["token"]))
    r = await _extend(h, driver, cancelled["id"], _plus(cancelled["ends_at"], hours=1))
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_extendable", r.text

    ok = (await book(h, driver, listing, start=window(h, 8)[0], end=window(h, 8)[1])).json()
    assert (await _extend(h, driver, ok["id"], _plus(ok["ends_at"], hours=1))).status_code == 200


async def test_only_the_driver_can_extend(h: Harness):
    host, _, driver, b = await _setup(h)
    stranger = await register(h)
    new_end = _plus(b["ends_at"], hours=1)
    assert (await _extend(h, host, b["id"], new_end)).status_code == 404
    assert (await _extend(h, stranger, b["id"], new_end)).status_code == 404
    assert (await _extend(h, stranger, b["id"], new_end, quote=True)).status_code == 404
    assert (await _extend(h, driver, str(uuid.uuid4()), new_end)).status_code == 404
    r = await h.client.post(f"/v1/bookings/{b['id']}/extend", json={"ends_at": new_end})
    assert r.status_code == 401
    assert (await _extend(h, driver, b["id"], new_end)).status_code == 200


async def test_online_extension_collects_only_the_difference(hp: Harness):
    host = await make_host(hp)
    listing = await create_listing(hp, host)
    driver = await register(hp)
    b = (await book(hp, driver, listing, slot_id=slot_id(listing))).json()
    order = (await hp.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))).json()
    sig = f"sig:{order['order_id']}:pay_1"
    r = await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": "pay_1", "signature": sig},
        headers=auth(driver["token"]),
    )
    assert r.status_code == 200, r.text

    r = await _extend(hp, driver, b["id"], _plus(b["ends_at"], hours=1))
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["status"] == "confirmed" and e["amount_paid"] == "94.40" and e["amount_due"] == "47.20"

    top_up = (await hp.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))).json()
    assert top_up["amount_minor"] == 4720 and top_up["order_id"] != order["order_id"]
    sig = f"sig:{top_up['order_id']}:pay_2"
    r = await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": top_up["order_id"], "payment_id": "pay_2", "signature": sig},
        headers=auth(driver["token"]),
    )
    assert r.status_code == 200, r.text
    final = (await hp.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()
    assert final["amount_paid"] == "141.60" and final["amount_due"] == "0.00"
