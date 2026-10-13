import json
from decimal import Decimal

from tests.conftest import Harness
from tests.helpers import auth, book, create_listing, make_host, parse, register, relogin, window


async def _paid_setup(hp: Harness, **listing_overrides):
    host = await make_host(hp)
    listing = await create_listing(hp, host, **listing_overrides)
    driver = await register(hp)
    return host, listing, driver


async def _pay(hp: Harness, driver: dict, booking_id: str) -> dict:
    r = await hp.client.post(f"/v1/bookings/{booking_id}/payment", headers=auth(driver["token"]))
    assert r.status_code == 200, r.text
    return r.json()


async def test_online_booking_confirms_only_after_verified_payment(hp: Harness):
    _, listing, driver = await _paid_setup(hp)
    b = (await book(hp, driver, listing)).json()
    assert b["status"] == "pending_payment" and b["hold_expires_at"] and b["payment_mode"] == "online"
    order = await _pay(hp, driver, b["id"])
    assert order["amount_minor"] == 9440 and order["key_id"] == "rzp_test_key"
    again = await _pay(hp, driver, b["id"])
    assert again["order_id"] == order["order_id"]  # double tap reuses the open order

    r = await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": "pay_1", "signature": "forged"},
        headers=auth(driver["token"]),
    )
    assert r.status_code == 403
    r = await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": "pay_1", "signature": f"sig:{order['order_id']}:pay_1"},
        headers=auth(driver["token"]),
    )
    assert r.status_code == 200, r.text
    b = (await hp.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()
    assert b["status"] == "confirmed" and b["amount_paid"] == "94.40" and b["amount_due"] == "0.00"
    r = await hp.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))
    assert r.json()["error"]["code"] == "not_payable"


async def test_webhook_capture_is_deduplicated(hp: Harness):
    _, listing, driver = await _paid_setup(hp)
    b = (await book(hp, driver, listing)).json()
    order = await _pay(hp, driver, b["id"])
    event = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_W1", "order_id": order["order_id"]}}},
    }
    body = json.dumps(event).encode()
    headers = {"x-razorpay-signature": "bad", "x-razorpay-event-id": "evt_1", "content-type": "application/json"}
    r = await hp.client.post("/v1/webhooks/razorpay", content=body, headers=headers)
    assert r.status_code == 401
    headers["x-razorpay-signature"] = "good"
    for _ in range(3):  # Razorpay retries deliver the same event id
        r = await hp.client.post("/v1/webhooks/razorpay", content=body, headers=headers)
        assert r.status_code == 200
    b = (await hp.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()
    assert b["status"] == "confirmed" and b["amount_paid"] == "94.40"
    assert await hp.container.webhook_bloom.might_contain("razorpay:evt_1")


async def test_hold_expiry_and_late_payment_refund(hp: Harness):
    from app.workers.jobs import maintenance, refund_payment

    _, listing, driver = await _paid_setup(hp)
    b = (await book(hp, driver, listing)).json()
    order = await _pay(hp, driver, b["id"])
    hp.clock.advance(minutes=11)
    await relogin(hp, driver)
    assert (await maintenance(hp.container))["expired"] == 1
    r = await hp.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))
    assert r.json()["error"]["code"] == "not_payable"
    # The payment still lands after expiry -> captured, booking stays expired, refund queued.
    r = await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": "pay_L", "signature": f"sig:{order['order_id']}:pay_L"},
        headers=auth(driver["token"]),
    )
    assert r.status_code == 200
    task, args = hp.jobs.calls[-1]
    assert task == "refund_payment"
    await refund_payment(hp.container, *args)
    assert hp.gateway.refunds == [("pay_L", Decimal("94.40"))]
    await refund_payment(hp.container, *args)  # retried job does not refund twice
    assert len(hp.gateway.refunds) == 1


async def test_late_cancellation_keeps_fee_and_refunds_rest(hp: Harness):
    _, listing, driver = await _paid_setup(hp)
    start, end = window(hp, start_in_hours=1, hours=2)
    b = (await book(hp, driver, listing, start=start, end=end)).json()
    order = await _pay(hp, driver, b["id"])
    await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": "pay_C", "signature": f"sig:{order['order_id']}:pay_C"},
        headers=auth(driver["token"]),
    )
    # Cancel 30 minutes before start: inside the 60-minute late-cancellation window.
    hp.clock.advance(seconds=(parse(b["starts_at"]) - hp.clock.now()).total_seconds() - 30 * 60)
    await relogin(hp, driver)
    r = await hp.client.post(
        f"/v1/bookings/{b['id']}/cancel", json={"reason": "plans changed"}, headers=auth(driver["token"])
    )
    assert r.json()["status"] == "cancelled"
    await hp.drain()
    await hp.drain()  # retry-safe: second drain must not refund again
    # subtotal 80 * 25% late fee = 20 kept; 94.40 - 20 = 74.40 refunded
    assert hp.gateway.refunds == [("pay_C", Decimal("74.40"))]


async def test_host_cancellation_refunds_everything(hp: Harness):
    host, listing, driver = await _paid_setup(hp)
    start, end = window(hp, start_in_hours=1, hours=2)
    b = (await book(hp, driver, listing, start=start, end=end)).json()
    order = await _pay(hp, driver, b["id"])
    await hp.client.post(
        f"/v1/bookings/{b['id']}/payment/confirm",
        json={"order_id": order["order_id"], "payment_id": "pay_H", "signature": f"sig:{order['order_id']}:pay_H"},
        headers=auth(driver["token"]),
    )
    r = await hp.client.post(f"/v1/bookings/{b['id']}/cancel", json={}, headers=auth(host["token"]))
    assert r.status_code == 200
    await hp.drain()
    assert hp.gateway.refunds == [("pay_H", Decimal("94.40"))]


async def test_payments_disabled_in_offline_mode(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing)).json()
    r = await h.client.post(f"/v1/bookings/{b['id']}/payment", headers=auth(driver["token"]))
    assert r.json()["error"]["code"] == "payments_disabled"
