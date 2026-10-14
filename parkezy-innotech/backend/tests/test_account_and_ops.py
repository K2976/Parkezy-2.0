"""Endpoints not covered elsewhere: password change, re-sent verification, push-token removal,
notification preferences, listing photos, driver self check-out, outbox admin and /metrics."""

from pydantic import SecretStr
from sqlalchemy import update

from app.db.models import OutboxEvent
from tests.conftest import Harness
from tests.helpers import (
    auth,
    book,
    code_from_email,
    create_listing,
    make_host,
    parse,
    register,
    relogin,
    upload_photo,
)


async def test_resend_verification_and_change_password(h: Harness):
    user = await register(h, verify=False)
    await h.drain()
    h.email.sent.clear()
    h.clock.advance(seconds=30)
    r = await h.client.post("/v1/auth/resend-verification", headers=auth(user["token"]))
    assert r.status_code == 200, r.text
    await h.drain()
    code = code_from_email(h, user["email"])
    r = await h.client.post("/v1/auth/verify-email", json={"code": code}, headers=auth(user["token"]))
    assert r.status_code == 200 and r.json()["email_verified"], r.text
    r = await h.client.post("/v1/auth/resend-verification", headers=auth(user["token"]))
    assert r.json()["error"]["code"] == "already_verified"

    body = {"current_password": "wrong-password", "new_password": "parking456"}
    r = await h.client.post("/v1/auth/change-password", json=body, headers=auth(user["token"]))
    assert r.status_code == 403 and r.json()["error"]["code"] == "invalid_credentials"
    body["current_password"] = "parking123"
    r = await h.client.post("/v1/auth/change-password", json=body, headers=auth(user["token"]))
    assert r.status_code == 200, r.text
    # Every session is revoked, the old password stops working, and the user is told by email.
    assert (await h.client.post("/v1/auth/refresh", json={"refresh_token": user["refresh"]})).status_code == 401
    login = {"email": user["email"], "password": "parking123"}
    assert (await h.client.post("/v1/auth/login", json=login)).status_code == 401
    login["password"] = "parking456"
    assert (await h.client.post("/v1/auth/login", json=login)).status_code == 200
    await h.drain()
    assert any(e.to == user["email"] and "password" in e.subject.lower() for e in h.email.sent)


async def test_push_token_removal_and_notification_preferences(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    token = {"token": "ExponentPushToken[driver-2]", "platform": "ios"}
    assert (await h.client.post("/v1/me/push-tokens", json=token, headers=auth(driver["token"]))).status_code == 204
    r = await h.client.post("/v1/me/push-tokens/remove", json=token, headers=auth(driver["token"]))
    assert r.status_code == 204
    await book(h, driver, listing)
    await h.drain()
    assert not any("ExponentPushToken[driver-2]" in m.tokens for m in h.push.sent)

    r = await h.client.get("/v1/me/notification-preferences", headers=auth(driver["token"]))
    assert r.status_code == 200, r.text
    r = await h.client.put(
        "/v1/me/notification-preferences", json={"email": {"receipts": False}}, headers=auth(driver["token"])
    )
    assert r.status_code == 200, r.text
    assert r.json()["email"]["receipts"] is False
    r = await h.client.get("/v1/me/notification-preferences", headers=auth(driver["token"]))
    assert r.json()["email"]["receipts"] is False


async def test_listing_photos_add_and_remove(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    only = listing["media"][0]["id"]
    url = f"/v1/host/listings/{listing['id']}/photos"
    # A live listing may not drop below the minimum photo count.
    r = await h.client.delete(f"{url}/{only}", headers=auth(host["token"]))
    assert r.json()["error"]["code"] == "photos_required"

    extra = await upload_photo(h, host["token"])
    r = await h.client.post(url, json={"upload_ids": [extra]}, headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    assert len(r.json()["media"]) == 2
    r = await h.client.delete(f"{url}/{only}", headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    assert [m["id"] for m in r.json()["media"]] != [only] and len(r.json()["media"]) == 1

    stranger = await make_host(h)
    r = await h.client.post(url, json={"upload_ids": [extra]}, headers=auth(stranger["token"]))
    assert r.status_code == 404


async def test_driver_can_check_out_themselves(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing)).json()
    r = await h.client.post(f"/v1/bookings/{b['id']}/check-out", headers=auth(driver["token"]))
    assert r.json()["error"]["code"] == "not_checked_in"

    h.clock.advance(seconds=(parse(b["starts_at"]) - h.clock.now()).total_seconds())
    await relogin(h, host, driver)
    creds = (await h.client.get(f"/v1/bookings/{b['id']}/access", headers=auth(driver["token"]))).json()
    r = await h.client.post("/v1/host/access/verify", json={"qr_token": creds["qr_token"]}, headers=auth(host["token"]))
    assert r.json()["action"] == "checked_in", r.text

    h.clock.advance(hours=1)
    await relogin(h, host, driver)
    assert (await h.client.post(f"/v1/bookings/{b['id']}/check-out", headers=auth(host["token"]))).status_code == 404
    r = await h.client.post(f"/v1/bookings/{b['id']}/check-out", headers=auth(driver["token"]))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"


async def test_admin_outbox_dead_letters_and_retry(h: Harness):
    admin = await register(h, "admin@test.parkezy.dev")
    user = await register(h)
    assert (await h.client.get("/v1/admin/outbox/stats", headers=auth(user["token"]))).status_code == 403

    h.email.fail = True
    await h.client.post("/v1/auth/forgot-password", json={"email": user["email"]})
    await h.drain()
    async with h.container.session_factory() as s:
        await s.execute(
            update(OutboxEvent)
            .where(OutboxEvent.processed_at.is_(None))
            .values(attempts=h.container.settings.outbox_max_attempts)
        )
        await s.commit()

    r = await h.client.get("/v1/admin/outbox/stats", headers=auth(admin["token"]))
    assert r.status_code == 200 and r.json()["dead"] >= 1, r.text
    dead = (await h.client.get("/v1/admin/outbox/dead-letters", headers=auth(admin["token"]))).json()
    assert dead and dead[0]["last_error"]

    h.email.fail = False
    for event in dead:
        r = await h.client.post(f"/v1/admin/outbox/{event['id']}/retry", headers=auth(admin["token"]))
        assert r.status_code == 200 and r.json()["attempts"] == 0, r.text
    assert ("process_outbox", ()) in h.jobs.calls
    await h.drain()
    assert (await h.client.get("/v1/admin/outbox/stats", headers=auth(admin["token"]))).json() == {
        "pending": 0,
        "dead": 0,
    }
    assert any(e.to == user["email"] for e in h.email.sent)
    missing = "00000000-0000-7000-8000-000000000000"
    assert (await h.client.post(f"/v1/admin/outbox/{missing}/retry", headers=auth(admin["token"]))).status_code == 404


async def test_metrics_endpoint_requires_token(h: Harness):
    settings = h.container.settings
    assert (await h.client.get("/metrics")).status_code == 404  # disabled without METRICS_TOKEN
    settings.metrics_token = SecretStr("scrape-me")
    try:
        assert (await h.client.get("/metrics")).status_code == 401
        r = await h.client.get("/metrics", headers={"Authorization": "Bearer scrape-me"})
        assert r.status_code == 200
        assert "parkezy_http_requests_total" in r.text and "parkezy_outbox_pending" in r.text
    finally:
        settings.metrics_token = None


async def test_unconfigured_resend_webhook_rejects_forged_signatures(h: Harness):
    import base64
    import hashlib
    import hmac

    assert h.container.settings.resend_webhook_secret is None  # blank in .env must mean "not configured"
    body = b'{"type":"email.bounced","data":{"to":["victim@test.parkezy.dev"]}}'
    ts = str(int(h.clock.now().timestamp()))
    forged = base64.b64encode(hmac.new(b"", f"msg_1.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    headers = {"svix-id": "msg_1", "svix-timestamp": ts, "svix-signature": f"v1,{forged}"}
    r = await h.client.post("/v1/webhooks/resend", content=body, headers=headers)
    assert r.status_code == 401

    from app.integrations.webhooks import verify_svix_signature

    assert not verify_svix_signature(
        secret="", msg_id="msg_1", timestamp=ts, signature_header=f"v1,{forged}", body=body, now=h.clock.now()
    )
