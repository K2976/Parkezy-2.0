"""Resend integration: request shape, error classification, delivery failure handling, webhooks,
abuse limits. The Resend API is always mocked (httpx.MockTransport or the harness fake)."""

import base64
import hashlib
import hmac
import json
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select

from app.core.errors import ExternalServiceError
from app.db.models import EmailLog, EmailSuppression, OutboxEvent
from app.integrations.email import OutgoingEmail, PermanentEmailError, ResendEmailSender
from app.services.factory import Services
from app.workers.outbox_processor import backoff
from tests.conftest import Harness, make_settings
from tests.helpers import register

EMAIL = OutgoingEmail(
    to="driver@example.com",
    subject="Your code",
    html="<p>123456</p>",
    text="123456",
    idempotency_key="evt-1:verify_email",
    tags={"template": "verify_email"},
)


async def _send(handler) -> str:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        sender = ResendEmailSender(client, "https://api.resend.test", "re_test", "Parkezy <noreply@mail.x.dev>", None)
        return await sender.send(EMAIL)


# ---------------------------------------------------------------- sender
async def test_resend_request_shape():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "4ef9a417-02e9-4d39-ad75-9611e0fcc33c"})

    assert await _send(handler) == "4ef9a417-02e9-4d39-ad75-9611e0fcc33c"
    request = seen[0]
    assert str(request.url) == "https://api.resend.test/emails"
    assert request.headers["authorization"] == "Bearer re_test"
    assert request.headers["idempotency-key"] == "evt-1:verify_email"
    body = json.loads(request.content)
    assert body["from"] == "Parkezy <noreply@mail.x.dev>" and body["to"] == ["driver@example.com"]
    assert body["html"] == "<p>123456</p>" and body["text"] == "123456"
    assert body["tags"] == [{"name": "template", "value": "verify_email"}]
    assert "reply_to" not in body


@pytest.mark.parametrize(
    ("status", "name", "permanent"),
    [
        (422, "validation_error", True),
        (400, "validation_error", True),
        (409, "invalid_idempotent_request", True),
        (409, "concurrent_idempotent_requests", False),
        (429, "rate_limit_exceeded", False),
        (429, "daily_quota_exceeded", False),
        (403, "validation_error", False),  # e.g. domain not verified: fixable config, keep retrying (bounded)
        (401, "missing_api_key", False),
        (500, "application_error", False),
    ],
)
async def test_resend_error_classification(status: int, name: str, permanent: bool):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"statusCode": status, "name": name, "message": "nope"})

    with pytest.raises(ExternalServiceError) as caught:
        await _send(handler)
    assert isinstance(caught.value, PermanentEmailError) is permanent
    assert caught.value.code == name
    assert caught.value.details == {"status": status, "name": name, "message": "nope"}
    assert "123456" not in str(caught.value.details)  # the request (with its code) is never echoed


async def test_resend_network_and_malformed_responses_are_retryable():
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    for handler in (
        unreachable,
        lambda r: httpx.Response(502, text="<html>bad gateway</html>"),
        lambda r: httpx.Response(200, json={}),
        lambda r: httpx.Response(200, json=["unexpected"]),
    ):
        with pytest.raises(ExternalServiceError) as caught:
            await _send(handler)
        assert not isinstance(caught.value, PermanentEmailError)


# ---------------------------------------------------------------- configuration
def test_email_settings_validation():
    with pytest.raises(ValidationError, match="RESEND_API_KEY"):
        make_settings(email_provider="resend", resend_api_key=None)
    with pytest.raises(ValidationError, match="EMAIL_FROM"):
        make_settings(email_from="Parkezy")
    with pytest.raises(ValidationError, match="console"):
        make_settings(app_env="staging", email_provider="console")
    s = make_settings(email_provider="resend", resend_api_key="re_x", email_from="Parkezy <noreply@mail.x.dev>")
    assert s.resend_api_key and s.resend_api_key.get_secret_value() == "re_x"
    assert "re_x" not in repr(s)  # SecretStr keeps the key out of logs and tracebacks


def test_outbox_backoff_is_jittered_and_capped():
    for attempts in range(1, 12):
        delay = min(15 * 2 ** (attempts - 1), 3600)
        for _ in range(20):
            got = backoff(attempts, 15, 3600)
            assert timedelta(seconds=delay * 0.75) <= got <= timedelta(seconds=delay)


# ---------------------------------------------------------------- delivery failures
async def test_permanent_rejection_is_recorded_and_not_retried(h: Harness):
    h.email.error = PermanentEmailError(
        "rejected", code="validation_error", details={"status": 422, "name": "validation_error", "message": "bad to"}
    )
    user = await register(h, verify=False)
    await h.drain()
    assert h.email.attempts == 1
    async with h.container.session_factory() as s:
        log = (await s.execute(select(EmailLog))).scalar_one()
        assert log.status == "failed" and "validation_error" in log.error
        event = (await s.execute(select(OutboxEvent))).scalar_one()
        assert event.processed_at is not None and event.last_error is None  # account creation unaffected
    h.clock.advance(hours=2)
    assert await h.drain() == 0 and h.email.attempts == 1
    r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "parking123"})
    assert r.status_code == 200
    # A handler retried because of a sibling send never re-attempts it, even if the provider would now
    # answer 409 invalid_idempotent_request (which must not be read as "sent").
    h.email.error = PermanentEmailError("rejected", code="invalid_idempotent_request", details={"status": 409})
    async with h.container.session_factory() as s:
        status = (
            await Services(h.container, s)
            .email()
            .send(to=user["email"], template="verify_email", context={}, dedupe_key=log.dedupe_key)
        )
        assert status == "failed" and h.email.attempts == 1


async def test_idempotent_replay_counts_as_sent(h: Harness):
    h.email.error = PermanentEmailError("rejected", code="invalid_idempotent_request", details={"status": 409})
    await register(h, verify=False)
    await h.drain()
    async with h.container.session_factory() as s:
        log = (await s.execute(select(EmailLog))).scalar_one()
        assert log.status == "sent" and log.provider_message_id is None


async def test_transient_failure_retries_until_sent_once(h: Harness):
    h.email.fail = True
    user = await register(h, verify=False)
    await h.drain()
    async with h.container.session_factory() as s:
        assert (await s.execute(select(EmailLog))).scalar_one().status == "failed"
    h.email.fail = False
    h.clock.advance(minutes=5)
    await h.drain()
    h.clock.advance(hours=2)
    await h.drain()
    assert [e.to for e in h.email.sent] == [user["email"]]
    async with h.container.session_factory() as s:
        assert (await s.execute(select(EmailLog))).scalar_one().status == "sent"


# ---------------------------------------------------------------- webhooks
SECRET_RAW = b"resend-test-secret"


def _signed(h: Harness, payload: object, msg_id: str = "msg_1") -> tuple[str, dict]:
    h.container.settings.resend_webhook_secret = SecretStr("whsec_" + base64.b64encode(SECRET_RAW).decode())
    body = json.dumps(payload)
    ts = str(int(h.clock.now().timestamp()))
    sig = base64.b64encode(hmac.new(SECRET_RAW, f"{msg_id}.{ts}.{body}".encode(), hashlib.sha256).digest()).decode()
    return body, {"svix-id": msg_id, "svix-timestamp": ts, "svix-signature": f"v1,{sig}"}


async def _webhook(h: Harness, payload: object, msg_id: str = "msg_1") -> httpx.Response:
    body, headers = _signed(h, payload, msg_id)
    return await h.client.post("/v1/webhooks/resend", content=body, headers=headers)


async def _log_status(h: Harness) -> str:
    async with h.container.session_factory() as s:
        return (await s.execute(select(EmailLog))).scalar_one().status


async def test_webhook_events_never_move_status_backwards(h: Harness):
    user = await register(h, verify=False)
    await h.drain()
    async with h.container.session_factory() as s:
        message_id = (await s.execute(select(EmailLog))).scalar_one().provider_message_id
    data = {"email_id": message_id, "to": [user["email"]]}
    assert (await _webhook(h, {"type": "email.delivered", "data": data}, "m1")).status_code == 200
    assert await _log_status(h) == "delivered"
    assert (await _webhook(h, {"type": "email.complained", "data": data}, "m2")).status_code == 200
    assert await _log_status(h) == "complained"
    # A late or redelivered "delivered" must not hide the complaint.
    assert (await _webhook(h, {"type": "email.delivered", "data": data}, "m1")).status_code == 200
    assert await _log_status(h) == "complained"
    assert (await _webhook(h, {"type": "email.opened", "data": data}, "m3")).status_code == 200
    async with h.container.session_factory() as s:
        assert await s.get(EmailSuppression, user["email"].lower())


async def test_webhook_suppressed_and_malformed_payloads(h: Harness):
    user = await register(h, verify=False)
    await h.drain()
    async with h.container.session_factory() as s:
        message_id = (await s.execute(select(EmailLog))).scalar_one().provider_message_id
    # `to` as a bare string must not be iterated character by character into the suppression list.
    r = await _webhook(h, {"type": "email.suppressed", "data": {"email_id": message_id, "to": user["email"]}})
    assert r.status_code == 200
    async with h.container.session_factory() as s:
        assert (await s.execute(select(EmailSuppression))).scalars().all() == []
    assert await _log_status(h) == "skipped"
    for bad in ([], {"type": "email.bounced"}, {"type": "email.bounced", "data": "x"}):
        assert (await _webhook(h, bad, "m9")).status_code == 422


# ---------------------------------------------------------------- abuse limits
async def test_reset_emails_are_limited_per_address_without_enumeration(h: Harness):
    user = await register(h, verify=False)
    for address in (user["email"], "nobody@test.parkezy.dev"):
        for _ in range(h.container.settings.rate_limit_email_per_window):
            r = await h.client.post("/v1/auth/forgot-password", json={"email": address})
            assert r.status_code == 200
        r = await h.client.post("/v1/auth/forgot-password", json={"email": address.upper()})
        assert r.status_code == 429  # same answer for real and unknown accounts
    r = await h.client.post("/v1/auth/forgot-password", json={"email": "someone-else@test.parkezy.dev"})
    assert r.status_code == 200
