"""Notifications, email delivery guarantees, disputes, account deletion, health."""

import base64
import hashlib
import hmac
import json

from sqlalchemy import select

from app.db.models import EmailLog, OutboxEvent
from tests.conftest import Harness
from tests.helpers import auth, book, create_listing, make_host, register, upload_photo


async def test_notifications_inbox_and_push(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    r = await h.client.post(
        "/v1/me/push-tokens",
        json={"token": "ExponentPushToken[driver-1]", "platform": "android"},
        headers=auth(driver["token"]),
    )
    assert r.status_code == 204
    await book(h, driver, listing)
    await h.drain()
    assert any(m.title == "Booking confirmed" for m in h.push.sent)
    r = await h.client.get("/v1/notifications", headers=auth(driver["token"]))
    data = r.json()
    assert data["unread_count"] >= 1 and data["items"][0]["title"] == "Booking confirmed"
    await h.client.post("/v1/notifications/read", json={}, headers=auth(driver["token"]))
    assert (await h.client.get("/v1/notifications", headers=auth(driver["token"]))).json()["unread_count"] == 0
    host_inbox = (await h.client.get("/v1/notifications", headers=auth(host["token"]))).json()
    assert host_inbox["items"][0]["title"] == "New booking"


async def test_outbox_retries_failed_email_without_duplicating_inbox(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    await book(h, driver, listing)
    h.email.fail = True
    await h.drain()
    async with h.container.session_factory() as s:
        failed = (await s.execute(select(OutboxEvent).where(OutboxEvent.last_error.is_not(None)))).scalars().all()
        assert failed and failed[0].processed_at is None
    h.email.fail = False
    h.clock.advance(minutes=5)  # past the retry backoff
    await h.drain()
    async with h.container.session_factory() as s:
        pending = (await s.execute(select(OutboxEvent).where(OutboxEvent.processed_at.is_(None)))).scalars().all()
        assert pending == []
    inbox = (await h.client.post("/v1/auth/login", json={"email": driver["email"], "password": "parking123"})).json()
    items = (await h.client.get("/v1/notifications", headers=auth(inbox["tokens"]["access_token"]))).json()["items"]
    assert [i["title"] for i in items].count("Booking confirmed") == 1
    assert [e.subject for e in h.email.sent].count(f"Booking confirmed · {listing['title']}") == 1


async def test_resend_webhook_marks_bounce_and_suppresses(h: Harness):
    secret_raw = b"resend-test-secret"
    h.container.settings.resend_webhook_secret = __import__("pydantic").SecretStr(
        "whsec_" + base64.b64encode(secret_raw).decode()
    )
    user = await register(h)  # verification email sent + logged
    async with h.container.session_factory() as s:
        log = (await s.execute(select(EmailLog))).scalars().first()
    body = json.dumps({"type": "email.bounced", "data": {"email_id": log.provider_message_id, "to": [user["email"]]}})
    ts = str(int(h.clock.now().timestamp()))
    sig = base64.b64encode(hmac.new(secret_raw, f"msg_1.{ts}.{body}".encode(), hashlib.sha256).digest()).decode()
    headers = {"svix-id": "msg_1", "svix-timestamp": ts, "svix-signature": f"v1,{sig}"}
    r = await h.client.post("/v1/webhooks/resend", content=body, headers=headers)
    assert r.status_code == 200, r.text
    r = await h.client.post("/v1/webhooks/resend", content=body, headers=headers | {"svix-signature": "v1,nope"})
    assert r.status_code == 401
    async with h.container.session_factory() as s:
        log = (await s.execute(select(EmailLog).where(EmailLog.id == log.id))).scalar_one()
        assert log.status == "bounced"
    sent_before = len(h.email.sent)
    await h.client.post("/v1/auth/forgot-password", json={"email": user["email"]})
    await h.drain()
    assert len(h.email.sent) == sent_before  # suppressed address is never emailed again


async def test_disputes_with_evidence_and_admin_review(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    admin = await register(h, "admin@test.parkezy.dev")
    b = (await book(h, driver, listing)).json()
    evidence = await upload_photo(h, driver["token"], purpose="dispute_evidence")
    r = await h.client.post(
        "/v1/disputes",
        json={
            "booking_id": b["id"],
            "reason": "spot_occupied",
            "description": "Another car was parked there",
            "evidence_upload_ids": [evidence],
        },
        headers=auth(driver["token"]),
    )
    assert r.status_code == 201, r.text
    dispute = r.json()
    assert len(dispute["evidence_urls"]) == 1
    r = await h.client.post(
        "/v1/disputes",
        json={"booking_id": b["id"], "reason": "other", "description": "Second report on same booking"},
        headers=auth(driver["token"]),
    )
    assert r.json()["error"]["code"] == "dispute_exists"
    r = await h.client.get("/v1/admin/disputes", headers=auth(driver["token"]))
    assert r.status_code == 403
    r = await h.client.get("/v1/admin/disputes", params={"status": "open"}, headers=auth(admin["token"]))
    assert [d["id"] for d in r.json()] == [dispute["id"]]
    r = await h.client.patch(
        f"/v1/admin/disputes/{dispute['id']}",
        json={"status": "resolved", "resolution": "Refund issued"},
        headers=auth(admin["token"]),
    )
    assert r.json()["status"] == "resolved"
    await h.drain()
    assert any(e.subject.startswith("Update on your") for e in h.email.sent)


async def test_account_deletion_policy_and_anonymisation(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing)).json()
    delete = {"password": "parking123"}
    r = await h.client.request("DELETE", "/v1/me", json=delete, headers=auth(driver["token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "active_bookings"
    await h.client.post(f"/v1/bookings/{b['id']}/cancel", json={}, headers=auth(driver["token"]))
    # Re-authentication: a valid session alone is not enough.
    r = await h.client.delete("/v1/me", headers=auth(driver["token"]))
    assert r.status_code == 422
    r = await h.client.request("DELETE", "/v1/me", json={"password": "wrong-pass"}, headers=auth(driver["token"]))
    assert r.status_code == 403 and r.json()["error"]["code"] == "invalid_credentials"
    r = await h.client.request("DELETE", "/v1/me", json=delete, headers=auth(driver["token"]))
    assert r.status_code == 200
    r = await h.client.get("/v1/me", headers=auth(driver["token"]))
    assert r.status_code == 401
    r = await h.client.post("/v1/auth/login", json={"email": driver["email"], "password": "parking123"})
    assert r.status_code == 401
    await h.drain()
    assert any(e.to == driver["email"] and "deleted" in e.subject for e in h.email.sent)
    # The email is free to register again.
    r = await h.client.post(
        "/v1/auth/register", json={"email": driver["email"], "password": "parking123", "full_name": "New Me"}
    )
    assert r.status_code == 201


async def test_health_and_error_contract(h: Harness):
    assert (await h.client.get("/health/live")).json() == {"status": "ok"}
    ready = await h.client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["checks"] == {"database": "ok", "redis": "ok"}
    r = await h.client.get("/v1/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = await h.client.get("/v1/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "not_authenticated"
    assert "x-request-id" in r.headers and "server-timing" in r.headers
