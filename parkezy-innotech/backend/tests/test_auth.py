from sqlalchemy import select

from app.db.models import OutboxEvent
from tests.conftest import Harness
from tests.helpers import auth, code_from_email, register


async def test_register_login_refresh_and_me(h: Harness):
    user = await register(h)
    r = await h.client.get("/v1/me", headers=auth(user["token"]))
    assert r.status_code == 200
    me = r.json()
    assert me["email_verified"] is True and me["is_host"] is False

    r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "parking123"})
    assert r.status_code == 200
    tokens = r.json()["tokens"]

    r = await h.client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["refresh_token"] != tokens["refresh_token"]


async def test_duplicate_email_and_bad_password(h: Harness):
    user = await register(h, verify=False)
    r = await h.client.post(
        "/v1/auth/register",
        json={"email": user["email"].upper(), "password": "parking123", "full_name": "Again"},
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_taken"
    r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "wrongpass1"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"


async def test_password_rules_and_validation_shape(h: Harness):
    r = await h.client.post("/v1/auth/register", json={"email": "not-an-email", "password": "short", "full_name": "X"})
    assert r.status_code == 422
    fields = {d["field"] for d in r.json()["error"]["details"]}
    assert {"email", "password", "full_name"} <= fields


async def test_refresh_token_reuse_revokes_family(h: Harness):
    user = await register(h, verify=False)
    first = user["refresh"]
    r = await h.client.post("/v1/auth/refresh", json={"refresh_token": first})
    second = r.json()["refresh_token"]
    # Replaying the rotated token is treated as theft...
    r = await h.client.post("/v1/auth/refresh", json={"refresh_token": first})
    assert r.status_code == 401 and r.json()["error"]["code"] == "refresh_reused"
    # ...and kills the newer token too.
    r = await h.client.post("/v1/auth/refresh", json={"refresh_token": second})
    assert r.status_code == 401


async def test_logout_revokes_refresh(h: Harness):
    user = await register(h, verify=False)
    await h.client.post("/v1/auth/logout", json={"refresh_token": user["refresh"]})
    r = await h.client.post("/v1/auth/refresh", json={"refresh_token": user["refresh"]})
    assert r.status_code == 401


async def test_access_token_expiry_uses_clock(h: Harness):
    user = await register(h, verify=False)
    h.clock.advance(minutes=16)
    r = await h.client.get("/v1/me", headers=auth(user["token"]))
    assert r.status_code == 401 and r.json()["error"]["code"] == "token_expired"


async def test_verification_code_attempt_limit(h: Harness):
    user = await register(h, verify=False)
    for _ in range(5):
        r = await h.client.post("/v1/auth/verify-email", json={"code": "000000"}, headers=auth(user["token"]))
        assert r.status_code == 422
    await h.drain()
    real = code_from_email(h, user["email"])
    r = await h.client.post("/v1/auth/verify-email", json={"code": real}, headers=auth(user["token"]))
    assert r.json()["error"]["code"] == "code_locked"


async def test_forgot_and_reset_password_flow(h: Harness):
    user = await register(h, verify=False)
    r = await h.client.post("/v1/auth/forgot-password", json={"email": "nobody@test.parkezy.dev"})
    assert r.status_code == 200  # no account enumeration
    r = await h.client.post("/v1/auth/forgot-password", json={"email": user["email"]})
    assert r.status_code == 200
    await h.drain()
    reset_mail = [e for e in h.email.sent if "Reset" in e.subject][-1]
    code = code_from_email(h, user["email"])
    assert code in reset_mail.text
    r = await h.client.post(
        "/v1/auth/reset-password", json={"email": user["email"], "code": code, "new_password": "newpass456"}
    )
    assert r.status_code == 200
    # old sessions are revoked
    r = await h.client.post("/v1/auth/refresh", json={"refresh_token": user["refresh"]})
    assert r.status_code == 401
    r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "newpass456"})
    assert r.status_code == 200
    await h.drain()
    assert any("password was changed" in e.subject for e in h.email.sent)


async def test_verification_code_is_scrubbed_from_outbox_after_sending(h: Harness):
    await register(h, verify=False)
    await h.drain()
    async with h.container.session_factory() as s:
        events = (await s.execute(select(OutboxEvent))).scalars().all()
        assert events and all("code" not in e.payload for e in events if e.processed_at)


async def test_codes_expire(h: Harness):
    user = await register(h, verify=False)
    await h.drain()
    code = code_from_email(h, user["email"])
    h.clock.advance(minutes=16)
    # token also expired; log in again
    r = await h.client.post("/v1/auth/login", json={"email": user["email"], "password": "parking123"})
    token = r.json()["tokens"]["access_token"]
    r = await h.client.post("/v1/auth/verify-email", json={"code": code}, headers=auth(token))
    assert r.json()["error"]["code"] == "invalid_code"


async def test_auth_rate_limit(h: Harness):
    original = h.container.settings.rate_limit_auth_per_window
    h.container.settings.rate_limit_auth_per_window = 3
    try:
        codes = []
        for _ in range(5):
            r = await h.client.post("/v1/auth/login", json={"email": "x@test.parkezy.dev", "password": "nope12345"})
            codes.append(r.status_code)
        assert codes[:3] == [401, 401, 401] and codes[3] == 429
        assert "retry-after" in {k.lower() for k in r.headers}
    finally:
        h.container.settings.rate_limit_auth_per_window = original


async def test_login_limit_per_account_survives_ip_rotation(h: Harness):
    settings = h.container.settings
    original = settings.rate_limit_auth_per_window, settings.trust_forwarded_for
    settings.rate_limit_auth_per_window, settings.trust_forwarded_for = 3, True
    try:
        codes = []
        for i in range(5):
            # A different client IP every time (as the proxy would append it): only the per-account limit can stop this.
            r = await h.client.post(
                "/v1/auth/login",
                json={"email": "victim@test.parkezy.dev", "password": f"guess{i}xyz"},
                headers={"x-forwarded-for": f"10.0.0.{i}"},
            )
            codes.append(r.status_code)
        assert codes[:3] == [401, 401, 401] and 429 in codes[3:]
    finally:
        settings.rate_limit_auth_per_window, settings.trust_forwarded_for = original


async def test_spoofed_forwarded_for_does_not_dodge_ip_limit(h: Harness):
    settings = h.container.settings
    original = settings.rate_limit_auth_per_window, settings.trust_forwarded_for
    settings.rate_limit_auth_per_window, settings.trust_forwarded_for = 3, True
    try:
        codes = []
        for i in range(5):
            # Client forges the first hop; the trusted proxy appends the real address last.
            r = await h.client.post(
                "/v1/auth/login",
                json={"email": f"user{i}@test.parkezy.dev", "password": "nope12345"},
                headers={"x-forwarded-for": f"6.6.6.{i}, 203.0.113.7"},
            )
            codes.append(r.status_code)
        assert codes[:3] == [401, 401, 401] and codes[3] == 429
    finally:
        settings.rate_limit_auth_per_window, settings.trust_forwarded_for = original


async def test_security_headers(h: Harness):
    r = await h.client.get("/health/live")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "max-age" in r.headers["strict-transport-security"]
