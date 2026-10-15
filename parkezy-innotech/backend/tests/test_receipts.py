"""Downloadable receipts / invoices.

Contract
--------
GET /v1/bookings/{booking_id}/receipt      -> 200 ReceiptOut (JSON)
GET /v1/bookings/{booking_id}/receipt.pdf  -> 200 application/pdf, Content-Disposition: attachment;
                                              filename="<invoice_number>.pdf"

ReceiptOut = {invoice_number, issued_at, booking_id, currency, payment_mode,
              listing: {title, address_line, city}, driver: {full_name}, host: {full_name},
              starts_at, ends_at, checked_in_at, checked_out_at,
              line_items: [{kind: parking|overstay|cancellation_fee|gst, description, amount}],
              subtotal, tax_amount, total, amount_paid, amount_due}

Rules
-----
* Available for completed bookings, cancelled bookings that kept a late-cancellation fee, and
  prepaid (online) no-shows, which are charged. Anything else (upcoming, free cancellation,
  pay-at-venue no-show, rejected) -> 409 `receipt_unavailable`.
* Driver and host of the booking may fetch it; anyone else 404; no token 401.
* invoice_number matches ^PKZ-\\d{4}-\\d{6}$, is assigned once on first issue, never changes, is unique,
  and increases with each new receipt.
* sum(line_items.amount) == total == booking final_amount.
"""

import asyncio
import re
import uuid
from decimal import Decimal

from tests.conftest import Harness
from tests.helpers import (
    auth,
    book,
    check_in,
    complete_booking,
    create_listing,
    make_host,
    parse,
    register,
    relogin,
    slot_id,
    window,
)

INVOICE = re.compile(r"^PKZ-\d{4}-\d{6}$")


async def _receipt(h: Harness, user: dict, booking_id: str, pdf: bool = False):
    suffix = ".pdf" if pdf else ""
    return await h.client.get(f"/v1/bookings/{booking_id}/receipt{suffix}", headers=auth(user["token"]))


async def _completed(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing, slot_id=slot_id(listing))).json()
    return host, listing, driver, await complete_booking(h, host, driver, b)


def _sum(items: list[dict]) -> Decimal:
    return sum((Decimal(i["amount"]) for i in items), Decimal("0"))


async def test_receipt_for_completed_booking(h: Harness):
    host, listing, driver, b = await _completed(h)
    r = await _receipt(h, driver, b["id"])
    assert r.status_code == 200, r.text
    rc = r.json()
    assert INVOICE.match(rc["invoice_number"]), rc["invoice_number"]
    assert rc["booking_id"] == b["id"] and rc["currency"] == "INR" and rc["payment_mode"] == "pay_at_venue"
    assert rc["listing"]["title"] == listing["title"]
    assert rc["driver"]["full_name"] == "Test User" and rc["host"]["full_name"] == "Test User"
    kinds = {i["kind"]: i["amount"] for i in rc["line_items"]}
    assert kinds == {"parking": "80.00", "gst": "14.40"}
    assert (rc["subtotal"], rc["tax_amount"], rc["total"]) == ("80.00", "14.40", "94.40")
    assert _sum(rc["line_items"]) == Decimal(rc["total"]) == Decimal(b["final_amount"])
    assert rc["amount_due"] == "0.00"

    # The host gets the very same invoice, and repeated fetches never re-number it.
    again = (await _receipt(h, host, b["id"])).json()
    assert again["invoice_number"] == rc["invoice_number"] and again["issued_at"] == rc["issued_at"]


async def test_overstay_appears_as_its_own_line(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing, slot_id=slot_id(listing))).json()
    await check_in(h, host, driver, b)
    h.clock.advance(seconds=(parse(b["ends_at"]) - h.clock.now()).total_seconds() + 20 * 60)
    await relogin(h, driver)
    done = (await h.client.post(f"/v1/bookings/{b['id']}/check-out", headers=auth(driver["token"]))).json()
    assert done["final_amount"] == "141.60"

    rc = (await _receipt(h, driver, b["id"])).json()
    kinds = {i["kind"]: i["amount"] for i in rc["line_items"]}
    assert kinds == {"parking": "80.00", "overstay": "40.00", "gst": "21.60"}
    assert rc["total"] == "141.60" and _sum(rc["line_items"]) == Decimal("141.60")


async def test_no_receipt_until_there_is_something_to_bill(h: Harness):
    from app.workers.jobs import maintenance

    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    upcoming = (await book(h, driver, listing)).json()
    r = await _receipt(h, driver, upcoming["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "receipt_unavailable", r.text
    assert (await _receipt(h, driver, upcoming["id"], pdf=True)).status_code == 409

    await h.client.post(f"/v1/bookings/{upcoming['id']}/cancel", json={}, headers=auth(driver["token"]))
    r = await _receipt(h, driver, upcoming["id"])  # free cancellation: nothing was charged
    assert r.json()["error"]["code"] == "receipt_unavailable"

    start, end = window(h, start_in_hours=1, hours=1)
    no_show = (await book(h, driver, listing, start=start, end=end)).json()
    h.clock.advance(hours=3)
    await maintenance(h.container)
    await relogin(h, driver)
    r = await _receipt(h, driver, no_show["id"])
    assert r.json()["error"]["code"] == "receipt_unavailable", r.text

    done = (await book(h, driver, listing, slot_id=slot_id(listing), start=window(h)[0], end=window(h)[1])).json()
    await complete_booking(h, host, driver, done)
    assert (await _receipt(h, driver, done["id"])).status_code == 200


async def test_late_cancellation_fee_receipt(hp: Harness):
    host = await make_host(hp)
    listing = await create_listing(hp, host)
    driver = await register(hp)
    start, end = window(hp, start_in_hours=2, hours=2)
    b = (await book(hp, driver, listing, slot_id=slot_id(listing), start=start, end=end)).json()
    order = (await hp.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))).json()
    await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": "pay_R", "signature": f"sig:{order['order_id']}:pay_R"},
        headers=auth(driver["token"]),
    )
    hp.clock.advance(seconds=(parse(b["starts_at"]) - hp.clock.now()).total_seconds() - 30 * 60)
    await relogin(hp, driver)
    await hp.client.post(f"/v1/bookings/{b['id']}/cancel", json={}, headers=auth(driver["token"]))
    await hp.drain()

    rc = (await _receipt(hp, driver, b["id"])).json()
    assert [i["kind"] for i in rc["line_items"]] == ["cancellation_fee"], rc
    assert rc["total"] == "20.00" and rc["payment_mode"] == "online"


async def test_pdf_download(h: Harness):
    _, _, driver, b = await _completed(h)
    number = (await _receipt(h, driver, b["id"])).json()["invoice_number"]
    r = await _receipt(h, driver, b["id"], pdf=True)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    disposition = r.headers["content-disposition"]
    assert disposition.startswith("attachment") and f"{number}.pdf" in disposition


async def test_pdf_first_then_json_share_the_invoice_number(h: Harness):
    _, _, driver, b = await _completed(h)
    assert (await _receipt(h, driver, b["id"], pdf=True)).status_code == 200
    number = (await _receipt(h, driver, b["id"])).json()["invoice_number"]
    assert number in (await _receipt(h, driver, b["id"], pdf=True)).headers["content-disposition"]


async def test_invoice_numbers_are_unique_and_increasing_even_under_concurrency(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host, slots=[{"label": f"S{i}"} for i in range(4)])
    drivers = [await register(h) for _ in range(4)]
    bookings = [(await book(h, d, listing, slot_id=slot_id(listing, f"S{i}"))).json() for i, d in enumerate(drivers)]
    for d, b in zip(drivers, bookings, strict=True):
        await check_in(h, host, d, b)
    h.clock.advance(seconds=(parse(bookings[0]["ends_at"]) - h.clock.now()).total_seconds())
    await relogin(h, host)
    for d, b in zip(drivers, bookings, strict=True):
        await relogin(h, d)
        assert (await h.client.post(f"/v1/bookings/{b['id']}/check-out", headers=auth(d["token"]))).status_code == 200

    # Driver and host race to issue the same receipt; plus all four issued at once.
    pairs = await asyncio.gather(
        *[_receipt(h, d, b["id"]) for d, b in zip(drivers, bookings, strict=True)],
        *[_receipt(h, host, b["id"]) for b in bookings],
    )
    assert all(r.status_code == 200 for r in pairs), [r.text for r in pairs]
    by_booking: dict[str, set[str]] = {}
    for r in pairs:
        by_booking.setdefault(r.json()["booking_id"], set()).add(r.json()["invoice_number"])
    assert all(len(v) == 1 for v in by_booking.values()), by_booking  # one number per booking
    numbers = sorted(next(iter(v)) for v in by_booking.values())
    assert len(set(numbers)) == 4

    later = await _completed(h)
    newest = (await _receipt(h, later[2], later[3]["id"])).json()["invoice_number"]
    assert newest > numbers[-1]


async def test_access_control(h: Harness):
    _, _, driver, b = await _completed(h)
    stranger = await register(h)
    assert (await _receipt(h, stranger, b["id"])).status_code == 404
    assert (await _receipt(h, stranger, b["id"], pdf=True)).status_code == 404
    assert (await _receipt(h, driver, str(uuid.uuid4()))).status_code == 404
    assert (await h.client.get(f"/v1/bookings/{b['id']}/receipt")).status_code == 401
    assert (await h.client.get(f"/v1/bookings/{b['id']}/receipt.pdf")).status_code == 401
    assert (await _receipt(h, driver, b["id"])).status_code == 200
