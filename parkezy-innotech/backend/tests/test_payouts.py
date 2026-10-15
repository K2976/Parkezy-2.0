"""Host payouts and withdrawals.

Contract
--------
PUT  /v1/host/payout-account        body {method: "upi", upi_id}
                                    or   {method: "bank_account", account_holder_name, account_number, ifsc}
                                    -> 200 PayoutAccountOut {method, upi_id?, account_holder_name?,
                                       account_number_last4?, ifsc?, updated_at}   (full number never returned)
GET  /v1/host/payout-account        -> 200 PayoutAccountOut, or 404 `no_payout_account`
GET  /v1/host/payouts/balance       -> 200 {currency, available, pending, paid_out}
POST /v1/host/payouts               body {amount}, header Idempotency-Key -> 201 PayoutOut (200 on replay)
GET  /v1/host/payouts               -> Page[PayoutOut], newest first
POST /v1/host/payouts/{id}/cancel   -> 200 PayoutOut (only while `requested`)
GET  /v1/admin/payouts?status=      -> Page[PayoutOut] (admin)
POST /v1/admin/payouts/{id}/mark-paid  body {reference}  -> 200 PayoutOut  (emails the host "Payout ...")
POST /v1/admin/payouts/{id}/reject     body {reason}     -> 200 PayoutOut  (money returns to available)

PayoutOut = {id, amount, currency, status: requested|paid|rejected|cancelled, method, reference,
             reject_reason, requested_at, paid_at}

Rules
-----
* available = money the platform owes the host (HOST_PAYABLE for online-paid bookings) minus
  requested + paid payouts. Pay-at-venue earnings are already in the host's hand -> not withdrawable.
* Requires a payout account (409 `no_payout_account`), amount > 0 with <= 2 dp (422),
  amount >= `min_payout_amount` platform setting, seed 100 (422 `below_minimum_payout`),
  amount <= available (409 `insufficient_balance`). Concurrent requests can never overdraw.
* Status transitions are one-way; anything else -> 409 `invalid_payout_transition`.
* Payout ledger entries keep the ledger balanced (sum == 0) and do not change lifetime
  `earnings_total` on the host dashboard.
"""

import asyncio
import uuid

from sqlalchemy import func, select

from app.db.models import LedgerEntry
from tests.conftest import Harness
from tests.helpers import (
    auth,
    book,
    complete_booking,
    create_listing,
    make_host,
    parse,
    register,
    relogin,
    slot_id,
    window,
)

UPI = {"method": "upi", "upi_id": "parkhost@okaxis"}
BANK = {
    "method": "bank_account",
    "account_holder_name": "Test Host",
    "account_number": "123456789012",
    "ifsc": "HDFC0001234",
}


async def _paid_completed_booking(hp: Harness, host: dict, listing: dict, *, hours: float = 10, start_in: float = 2):
    """An online-paid booking that completes: host earns rate * hours * 0.85 (A1 @ 40/h -> 340 for 10 h)."""
    driver = await register(hp)
    start, end = window(hp, start_in_hours=start_in, hours=hours)
    b = (await book(hp, driver, listing, slot_id=slot_id(listing), start=start, end=end)).json()
    order = (await hp.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))).json()
    pid = f"pay_{uuid.uuid4().hex[:8]}"
    r = await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": pid, "signature": f"sig:{order['order_id']}:{pid}"},
        headers=auth(driver["token"]),
    )
    assert r.status_code == 200, r.text
    return await complete_booking(hp, host, driver, b)


async def _host_with_balance(hp: Harness, account: dict | None = UPI):
    host = await make_host(hp)
    listing = await create_listing(hp, host)
    await _paid_completed_booking(hp, host, listing)
    if account:
        r = await hp.client.put("/v1/host/payout-account", json=account, headers=auth(host["token"]))
        assert r.status_code == 200, r.text
    return host, listing


async def _request(hp: Harness, host: dict, amount: str, key: str | None = None):
    return await hp.client.post(
        "/v1/host/payouts",
        json={"amount": amount},
        headers=auth(host["token"]) | {"Idempotency-Key": key or uuid.uuid4().hex},
    )


async def _balance(hp: Harness, host: dict) -> dict:
    r = await hp.client.get("/v1/host/payouts/balance", headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    return r.json()


async def _ledger_sum(hp: Harness):
    async with hp.container.session_factory() as s:
        return await s.scalar(select(func.coalesce(func.sum(LedgerEntry.amount), 0)))


async def test_full_payout_lifecycle(hp: Harness):
    host, _ = await _host_with_balance(hp)
    admin = await register(hp, "admin@test.parkezy.dev")
    assert await _balance(hp, host) == {"currency": "INR", "available": "340.00", "pending": "0.00", "paid_out": "0.00"}

    r = await _request(hp, host, "300.00")
    assert r.status_code == 201, r.text
    p = r.json()
    assert (p["amount"], p["status"], p["method"]) == ("300.00", "requested", "upi")
    assert await _balance(hp, host) == {
        "currency": "INR",
        "available": "40.00",
        "pending": "300.00",
        "paid_out": "0.00",
    }

    listed = await hp.client.get("/v1/admin/payouts", params={"status": "requested"}, headers=auth(admin["token"]))
    assert listed.status_code == 200 and [x["id"] for x in listed.json()["items"]] == [p["id"]], listed.text

    r = await hp.client.post(
        f"/v1/admin/payouts/{p['id']}/mark-paid", json={"reference": "UTR123456"}, headers=auth(admin["token"])
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paid" and r.json()["reference"] == "UTR123456" and r.json()["paid_at"]
    assert await _balance(hp, host) == {
        "currency": "INR",
        "available": "40.00",
        "pending": "0.00",
        "paid_out": "300.00",
    }

    r = await hp.client.post(
        f"/v1/admin/payouts/{p['id']}/mark-paid", json={"reference": "again"}, headers=auth(admin["token"])
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_payout_transition"
    r = await hp.client.post(f"/v1/host/payouts/{p['id']}/cancel", headers=auth(host["token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_payout_transition"

    assert await _ledger_sum(hp) == 0
    dash = (await hp.client.get("/v1/host/dashboard", headers=auth(host["token"]))).json()
    assert dash["earnings_total"] == "340.00"  # lifetime earnings are not reduced by withdrawals

    await hp.drain()
    host_email = (await hp.client.get("/v1/me", headers=auth(host["token"]))).json()["email"]
    assert any(e.to == host_email and "Payout" in e.subject for e in hp.email.sent)

    mine = (await hp.client.get("/v1/host/payouts", headers=auth(host["token"]))).json()
    assert [x["id"] for x in mine["items"]] == [p["id"]]


async def test_reject_and_cancel_return_the_money(hp: Harness):
    host, _ = await _host_with_balance(hp)
    admin = await register(hp, "admin@test.parkezy.dev")
    first = (await _request(hp, host, "200.00")).json()
    r = await hp.client.post(
        f"/v1/admin/payouts/{first['id']}/reject", json={"reason": "UPI id bounced"}, headers=auth(admin["token"])
    )
    assert r.status_code == 200 and r.json()["status"] == "rejected" and r.json()["reject_reason"] == "UPI id bounced"
    assert (await _balance(hp, host))["available"] == "340.00"

    second = (await _request(hp, host, "150.00")).json()
    assert (await _balance(hp, host))["available"] == "190.00"
    r = await hp.client.post(f"/v1/host/payouts/{second['id']}/cancel", headers=auth(host["token"]))
    assert r.status_code == 200 and r.json()["status"] == "cancelled", r.text
    assert await _balance(hp, host) == {"currency": "INR", "available": "340.00", "pending": "0.00", "paid_out": "0.00"}

    r = await hp.client.post(
        f"/v1/admin/payouts/{second['id']}/mark-paid", json={"reference": "x"}, headers=auth(admin["token"])
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_payout_transition"
    assert await _ledger_sum(hp) == 0


async def test_amount_rules(hp: Harness):
    host, _ = await _host_with_balance(hp)
    for bad in ("0", "-5", "100.001", "abc"):
        r = await _request(hp, host, bad)
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_failed", (bad, r.text)
    r = await _request(hp, host, "99.99")
    assert r.status_code == 422 and r.json()["error"]["code"] == "below_minimum_payout", r.text
    r = await _request(hp, host, "340.01")
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_balance", r.text
    r = await _request(hp, host, "340.00")  # the whole balance is fine
    assert r.status_code == 201, r.text
    assert (await _balance(hp, host))["available"] == "0.00"
    r = await _request(hp, host, "100.00")
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_balance"


async def test_payout_account_is_required_and_validated(hp: Harness):
    host, _ = await _host_with_balance(hp, account=None)
    r = await hp.client.get("/v1/host/payout-account", headers=auth(host["token"]))
    assert r.status_code == 404 and r.json()["error"]["code"] == "no_payout_account"
    r = await _request(hp, host, "200.00")
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_payout_account", r.text

    bad_accounts = [
        {"method": "upi", "upi_id": "no-at-sign"},
        {"method": "upi", "upi_id": "a@b@c"},
        {"method": "upi"},
        BANK | {"ifsc": "hdfc0001234x"},
        BANK | {"ifsc": "HDFC1001234"},  # 5th character must be 0
        BANK | {"account_number": "12ab5678901"},
        BANK | {"account_number": "12345678"},  # too short (9-18 digits)
        BANK | {"account_holder_name": " "},
        {"method": "paypal", "email": "x@y.z"},
    ]
    for body in bad_accounts:
        r = await hp.client.put("/v1/host/payout-account", json=body, headers=auth(host["token"]))
        assert r.status_code == 422, (body, r.text)

    r = await hp.client.put("/v1/host/payout-account", json=BANK, headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    acct = r.json()
    assert acct["method"] == "bank_account" and acct["account_number_last4"] == "9012" and acct["ifsc"] == "HDFC0001234"
    assert "123456789012" not in r.text
    r = await hp.client.get("/v1/host/payout-account", headers=auth(host["token"]))
    assert r.status_code == 200 and "123456789012" not in r.text

    # Switching method replaces the old account entirely.
    r = await hp.client.put("/v1/host/payout-account", json=UPI, headers=auth(host["token"]))
    assert r.json()["method"] == "upi" and r.json()["upi_id"] == "parkhost@okaxis"
    assert r.json().get("account_number_last4") is None
    assert (await _request(hp, host, "200.00")).status_code == 201


async def test_idempotent_request(hp: Harness):
    host, _ = await _host_with_balance(hp)
    key = uuid.uuid4().hex
    first = await _request(hp, host, "150.00", key)
    again = await _request(hp, host, "150.00", key)
    assert first.status_code == 201 and again.status_code == 200, again.text
    assert first.json()["id"] == again.json()["id"]
    assert (await _balance(hp, host))["available"] == "190.00"  # charged once
    mismatch = await _request(hp, host, "120.00", key)
    assert mismatch.status_code == 409 and mismatch.json()["error"]["code"] == "idempotency_mismatch"


async def test_concurrent_requests_cannot_overdraw(hp: Harness):
    host, _ = await _host_with_balance(hp)
    responses = await asyncio.gather(*[_request(hp, host, "300.00") for _ in range(6)])
    codes = sorted(r.status_code for r in responses)
    assert codes.count(201) == 1, codes
    assert all(r.json()["error"]["code"] == "insufficient_balance" for r in responses if r.status_code == 409)
    assert (await _balance(hp, host))["available"] == "40.00"


async def test_pay_at_venue_earnings_are_not_withdrawable(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing, slot_id=slot_id(listing))).json()
    await complete_booking(h, host, driver, b)
    dash = (await h.client.get("/v1/host/dashboard", headers=auth(host["token"]))).json()
    assert dash["earnings_total"] == "68.00"  # earned...
    bal = await _balance(h, host)
    assert bal["available"] == "0.00"  # ...but the host already holds the cash
    await h.client.put("/v1/host/payout-account", json=UPI, headers=auth(host["token"]))
    r = await _request(h, host, "100.00")
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_balance"


async def test_new_host_has_zero_balance(hp: Harness):
    host = await make_host(hp)
    assert await _balance(hp, host) == {"currency": "INR", "available": "0.00", "pending": "0.00", "paid_out": "0.00"}
    assert (await hp.client.get("/v1/host/payouts", headers=auth(host["token"]))).json()["items"] == []


async def test_permissions(hp: Harness):
    host, _ = await _host_with_balance(hp)
    other_host = await make_host(hp)
    driver = await register(hp)
    p = (await _request(hp, host, "200.00")).json()

    for method, path in (
        ("get", "/v1/host/payouts/balance"),
        ("get", "/v1/host/payouts"),
        ("get", "/v1/host/payout-account"),
    ):
        r = await getattr(hp.client, method)(path, headers=auth(driver["token"]))
        assert r.status_code == 403 and r.json()["error"]["code"] == "not_a_host", (path, r.text)
        assert (await getattr(hp.client, method)(path)).status_code == 401
    assert (await _request(hp, driver, "200.00")).status_code == 403

    # Another host can neither see nor cancel someone else's payout.
    r = await hp.client.post(f"/v1/host/payouts/{p['id']}/cancel", headers=auth(other_host["token"]))
    assert r.status_code == 404
    assert (await hp.client.get("/v1/host/payouts", headers=auth(other_host["token"]))).json()["items"] == []

    for path, body in (
        ("/v1/admin/payouts", None),
        (f"/v1/admin/payouts/{p['id']}/mark-paid", {"reference": "x"}),
        (f"/v1/admin/payouts/{p['id']}/reject", {"reason": "x"}),
    ):
        r = (
            await hp.client.get(path, headers=auth(host["token"]))
            if body is None
            else await hp.client.post(path, json=body, headers=auth(host["token"]))
        )
        assert r.status_code == 403, (path, r.text)

    admin = await register(hp, "admin@test.parkezy.dev")
    missing = str(uuid.uuid4())
    r = await hp.client.post(
        f"/v1/admin/payouts/{missing}/mark-paid", json={"reference": "x"}, headers=auth(admin["token"])
    )
    assert r.status_code == 404
    r = await hp.client.post(
        f"/v1/admin/payouts/{p['id']}/mark-paid", json={"reference": " "}, headers=auth(admin["token"])
    )
    assert r.status_code == 422
    r = await hp.client.post(f"/v1/admin/payouts/{p['id']}/reject", json={}, headers=auth(admin["token"]))
    assert r.status_code == 422


async def test_balance_grows_with_more_paid_bookings_and_late_cancellation_fees(hp: Harness):
    host, listing = await _host_with_balance(hp)
    await _paid_completed_booking(hp, host, listing, hours=2, start_in=2)  # +68.00
    assert (await _balance(hp, host))["available"] == "408.00"

    # A paid booking cancelled late keeps a fee: 25% of the 80.00 subtotal = 20.00, host gets 85% = 17.00.
    driver = await register(hp)
    start, end = window(hp, start_in_hours=2, hours=2)
    b = (await book(hp, driver, listing, slot_id=slot_id(listing), start=start, end=end)).json()
    order = (await hp.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))).json()
    await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={
            "order_id": order["order_id"],
            "payment_id": "pay_late",
            "signature": f"sig:{order['order_id']}:pay_late",
        },
        headers=auth(driver["token"]),
    )
    hp.clock.advance(seconds=(parse(b["starts_at"]) - hp.clock.now()).total_seconds() - 30 * 60)
    await relogin(hp, driver, host)
    r = await hp.client.post(f"/v1/bookings/{b['id']}/cancel", json={}, headers=auth(driver["token"]))
    assert r.json()["status"] == "cancelled", r.text
    await hp.drain()
    assert (await _balance(hp, host))["available"] == "425.00"
