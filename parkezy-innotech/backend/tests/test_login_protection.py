"""Adaptive login abuse protection (app/services/login_protection.py).

HTTP tests run the real stack (Postgres, Redis, argon2). The risk guard gets a fixed clock so window
boundaries never make a threshold flaky, and a fake CAPTCHA provider where challenges are involved.
"""

import asyncio
import uuid

import httpx
import pytest
from redis.asyncio import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.core.config import DEFAULT_LOGIN_RISK_RULES, RiskRule
from app.core.errors import ChallengeRequired, RateLimited
from app.integrations.challenge import ChallengeResult, NoChallengeVerifier, TurnstileVerifier
from app.services.login_protection import (
    LoginContext,
    LoginProtection,
    RiskLevel,
    Signals,
    score,
    subnet_of,
)
from tests.conftest import Harness
from tests.helpers import register

# Middle of a 900 s and of a 60 s window, so the previous window weighs exactly 0.5 (and is empty).
FIXED_NOW = 1_800_000_450.0
APP_UA = "okhttp/4.12.0"  # what the React Native app sends on Android
PASSWORD = "parking123"  # tests.helpers.register


class FakeChallenge:
    provider = "turnstile"
    site_key: str | None = "site-key-test"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def verify(self, token: str, remote_ip: str | None) -> ChallengeResult:
        self.calls.append(token)
        if token == "boom":
            raise RuntimeError("provider client bug")
        if token.startswith("valid"):
            return ChallengeResult(True, "ok")
        if token == "expired":
            return ChallengeResult(False, "expired")
        return ChallengeResult(False, "rejected:invalid-input-response")


def install_guard(h: Harness, challenge=None, redis: Redis | None = None) -> LoginProtection:
    c = h.container
    guard = LoginProtection(
        c.settings, redis or c.redis, c.one_time, challenge or NoChallengeVerifier(), now=lambda: FIXED_NOW
    )
    c.login_guard = guard
    return guard


def count_verifies(h: Harness, monkeypatch) -> list[int]:
    calls: list[int] = []
    original = h.container.hasher.verify_async

    async def spy(password_hash: str, password: str) -> bool:
        calls.append(1)
        return await original(password_hash, password)

    monkeypatch.setattr(h.container.hasher, "verify_async", spy)
    return calls


async def attempt(
    h: Harness, email: str, password: str = "wrong-pass-1", *, ip=None, device=None, token=None, ua=APP_UA
):
    headers = {"user-agent": ua}
    if ip:
        headers["x-forwarded-for"] = ip
    if device:
        headers["x-device-id"] = device
    body = {"email": email, "password": password}
    if token is not None:
        body["challenge_token"] = token
    return await h.client.post("/v1/auth/login", json=body, headers=headers)


def ctx(email="someone@test.parkezy.dev", ip="198.51.100.7", device=None, ua=APP_UA) -> LoginContext:
    return LoginContext.build(ip=ip, email=email, device_header=device, user_agent=ua)


def device_id() -> str:
    return uuid.uuid4().hex


# ================================================================ pure scoring


def test_score_is_deterministic_and_combines_signals():
    rules = DEFAULT_LOGIN_RISK_RULES
    assert score(Signals(), rules, 40, 80).level is RiskLevel.LOW
    a = score(Signals(account_failures=5, ip_failures=5), rules, 40, 80)
    b = score(Signals(account_failures=5, ip_failures=5), rules, 40, 80)
    assert a == b and a.score == 45 and a.level is RiskLevel.MEDIUM
    assert a.reasons == ("account_failures=5:+25", "ip_failures=5:+20")
    # caps: 100 failures count like 15
    assert score(Signals(account_failures=100), rules, 40, 80).score == 75
    # a recognised device lowers the score but never below zero
    assert score(Signals(known_device=True), rules, 40, 80).score == 0
    assert score(Signals(account_failures=10, account_distinct_ips=10, known_device=True), rules, 40, 80).score == 60


def test_no_single_signal_can_reach_high_risk_with_default_rules():
    worst = {
        name: (rule.threshold * rule.cap if isinstance(getattr(Signals(), name), int) else True)
        for name, rule in DEFAULT_LOGIN_RISK_RULES.items()
        if rule.weight > 0
    }
    for name, value in worst.items():
        result = score(Signals(**{name: value}), DEFAULT_LOGIN_RISK_RULES, 40, 80)
        assert result.level is not RiskLevel.HIGH, name


def test_rules_are_configurable():
    rules = DEFAULT_LOGIN_RISK_RULES | {"account_failures": RiskRule(threshold=1, weight=90, cap=1)}
    assert score(Signals(account_failures=1), rules, 40, 80).level is RiskLevel.HIGH


def test_subnet_grouping():
    assert subnet_of("203.0.113.77") == "203.0.113.0/24"
    assert subnet_of("2001:db8:1:2:3:4:5:6") == "2001:db8:1:2::/64"
    assert subnet_of("not-an-ip") == "not-an-ip"


def test_device_id_header_is_validated():
    assert ctx(device="x" * 10).device_id is None  # too short
    assert ctx(device="bad id with spaces!!").device_id is None
    assert ctx(device="a" * 129).device_id is None
    good = device_id()
    assert ctx(device=good).device_id == good


# ================================================================ Turnstile verifier (mocked provider)


def turnstile(handler, **overrides) -> TurnstileVerifier:
    options = dict(
        verify_url="https://challenges.example/siteverify",
        secret_key="secret-test",
        site_key="site-test",
        expected_hostnames=["app.parkezy.test"],
        expected_action="login",
        max_age_seconds=300,
        now=lambda: 1_800_000_000.0,
    )
    options.update(overrides)
    return TurnstileVerifier(httpx.AsyncClient(transport=httpx.MockTransport(handler)), **options)


def provider_says(**data):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=data)

    return handler


GOOD = {"success": True, "hostname": "app.parkezy.test", "action": "login", "challenge_ts": "2027-01-15T08:00:00Z"}
# 1_800_000_000 = 2027-01-15T08:00:00Z


async def test_turnstile_accepts_valid_token_and_sends_secret_and_ip():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(200, json=GOOD)

    result = await turnstile(handler).verify("tok-123", "198.51.100.7")
    assert result.ok
    assert seen["form"] == {"secret": "secret-test", "response": "tok-123", "remoteip": "198.51.100.7"}


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        ({"success": False, "error-codes": ["invalid-input-response"]}, "rejected:invalid-input-response"),
        ({"success": False, "error-codes": ["timeout-or-duplicate"]}, "rejected:timeout-or-duplicate"),
        ({**GOOD, "hostname": "evil.example"}, "hostname_mismatch"),
        ({**GOOD, "action": "signup"}, "action_mismatch"),
        ({**GOOD, "challenge_ts": "2027-01-15T07:54:59Z"}, "expired"),  # 301 s old
        ({k: v for k, v in GOOD.items() if k != "challenge_ts"}, "missing_timestamp"),
        ({"success": "true"}, "rejected:"),  # only a real boolean true counts
    ],
)
async def test_turnstile_rejections(data, reason):
    result = await turnstile(provider_says(**data)).verify("tok", None)
    assert not result.ok and result.reason == reason


async def test_turnstile_fails_closed_when_provider_is_down():
    def error(request):
        return httpx.Response(503)

    def broken(request):
        raise httpx.ConnectTimeout("timeout")

    def garbage(request):
        return httpx.Response(200, content=b"<html>")

    for handler in (error, broken, garbage):
        result = await turnstile(handler).verify("tok", None)
        assert not result.ok and result.reason == "provider_unavailable"


async def test_turnstile_rejects_malformed_tokens_without_calling_provider():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=GOOD)

    v = turnstile(handler)
    assert (await v.verify("", None)).reason == "malformed_token"
    assert (await v.verify("x" * 2049, None)).reason == "malformed_token"
    assert calls == []


# ================================================================ 1, 2, 13: normal login and enumeration


async def test_normal_login_with_valid_credentials(h: Harness):
    install_guard(h)
    user = await register(h, verify=False)
    r = await attempt(h, user["email"], PASSWORD, device=device_id())
    assert r.status_code == 200, r.text
    assert r.json()["tokens"]["access_token"]


async def test_nonexistent_account_and_wrong_password_look_identical(h: Harness, monkeypatch):
    install_guard(h)
    user = await register(h, verify=False)
    verifies = count_verifies(h, monkeypatch)
    wrong = await attempt(h, user["email"], "not-the-password")
    missing = await attempt(h, "nobody-here@test.parkezy.dev", "not-the-password")
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()
    assert set(wrong.headers) - {"x-request-id", "server-timing"} == set(missing.headers) - {
        "x-request-id",
        "server-timing",
    }
    # both paths run exactly one argon2 verification (unknown emails hit the dummy hash)
    assert len(verifies) == 2


async def test_risk_escalates_the_same_for_existing_and_nonexistent_accounts(h: Harness):
    install_guard(h, FakeChallenge())
    user = await register(h, verify=False)

    async def codes(email: str, ip: str) -> list[int]:
        return [(await attempt(h, email, ip=ip)).status_code for _ in range(6)]

    h.container.settings.trust_forwarded_for = True
    try:
        real = await codes(user["email"], "203.0.113.10")
        fake = await codes("ghost@test.parkezy.dev", "198.51.100.10")
    finally:
        h.container.settings.trust_forwarded_for = False
    assert real == fake == [401, 401, 401, 401, 401, 403]


# ================================================================ 4, 11, 12: one account, proportionate response


async def test_repeated_attempts_against_one_account_escalate_without_hashing(h: Harness, monkeypatch):
    install_guard(h, FakeChallenge())
    user = await register(h, verify=False)
    verifies = count_verifies(h, monkeypatch)

    codes = [(await attempt(h, user["email"])).status_code for _ in range(5)]
    assert codes == [401] * 5  # five typos are still just wrong passwords
    assert len(verifies) == 5

    # 5 failures on the account + 5 from this IP = medium: challenge before any hashing
    r = await attempt(h, user["email"])
    assert r.status_code == 403 and r.json()["error"]["code"] == "challenge_required"
    assert r.json()["error"]["details"] == {"provider": "turnstile", "site_key": "site-key-test"}
    assert len(verifies) == 5

    # solving challenges lets the guesses through (they are verified, and fail) ...
    for i in range(5):
        r = await attempt(h, user["email"], token=f"valid-{i}")
        assert r.status_code == 401
    assert len(verifies) == 10
    # ... until 10 + 10 failures = high: temporary 429, still no hashing
    r = await attempt(h, user["email"], token="valid-x")
    assert r.status_code == 429
    assert r.headers["retry-after"] == str(h.container.settings.login_throttle_retry_seconds)
    assert "score" not in r.text and "reason" not in r.text
    assert len(verifies) == 10


async def test_a_few_typos_then_success_is_not_challenged_and_resets_account(h: Harness):
    guard = install_guard(h, FakeChallenge())
    user = await register(h, verify=False)
    for _ in range(3):
        assert (await attempt(h, user["email"])).status_code == 401
    assert (await attempt(h, user["email"], PASSWORD)).status_code == 200
    assessment = await guard._assess(ctx(email=user["email"], ip="127.0.0.1"))
    assert "account_failures" not in " ".join(assessment.reasons)


async def test_victim_on_known_device_is_challenged_not_locked_out(h: Harness):
    """Lockout abuse: an attacker hammering a victim's account from many IPs."""
    install_guard(h, FakeChallenge())
    user = await register(h, verify=False)
    phone = device_id()
    h.container.settings.trust_forwarded_for = True
    try:
        assert (await attempt(h, user["email"], PASSWORD, ip="192.0.2.50", device=phone)).status_code == 200
        for i in range(12):
            await attempt(h, user["email"], ip=f"10.{i}.0.1", token=f"valid-attacker-{i}")
        # attacker's next try (unknown device): high risk, rejected
        assert (await attempt(h, user["email"], ip="10.99.0.1", token="valid-a")).status_code == 429
        # the real owner on their usual phone: only a challenge, then in
        r = await attempt(h, user["email"], PASSWORD, ip="192.0.2.50", device=phone)
        assert r.status_code == 403 and r.json()["error"]["code"] == "challenge_required"
        r = await attempt(h, user["email"], PASSWORD, ip="192.0.2.50", device=phone, token="valid-owner")
        assert r.status_code == 200
    finally:
        h.container.settings.trust_forwarded_for = False


# ================================================================ 3, 5: distributed attacks


async def test_rotating_ips_does_not_reset_account_risk(h: Harness):
    install_guard(h, FakeChallenge())
    h.container.settings.trust_forwarded_for = True
    try:
        codes = [(await attempt(h, "target@test.parkezy.dev", ip=f"203.0.{i}.9")).status_code for i in range(6)]
    finally:
        h.container.settings.trust_forwarded_for = False
    # every request came from a new /24, yet account failures + distinct IPs reach medium
    assert codes == [401, 401, 401, 401, 401, 403]


async def test_distributed_credential_stuffing_challenges_unknown_devices(h: Harness, monkeypatch):
    settings = h.container.settings
    monkeypatch.setattr(settings, "login_risk_rules", {"global_failures": RiskRule(threshold=10, weight=40)})
    install_guard(h, FakeChallenge())
    regular = await register(h, verify=False)
    phone = device_id()
    monkeypatch.setattr(settings, "trust_forwarded_for", True)
    assert (await attempt(h, regular["email"], PASSWORD, ip="192.0.2.1", device=phone)).status_code == 200

    # botnet: every request a different IP, subnet and account, one guess each
    for i in range(10):
        r = await attempt(h, f"leaked{i}@test.parkezy.dev", ip=f"100.{i}.{i}.1")
        assert r.status_code == 401
    # attack in progress: a fresh source on a fresh account is now challenged ...
    r = await attempt(h, "leaked99@test.parkezy.dev", ip="100.99.99.1")
    assert r.status_code == 403
    # ... while a regular user on their known device still signs in normally
    assert (await attempt(h, regular["email"], PASSWORD, ip="192.0.2.1", device=phone)).status_code == 200


async def test_one_source_trying_many_accounts(h: Harness):
    install_guard(h, FakeChallenge())
    codes = [(await attempt(h, f"victim{i}@test.parkezy.dev")).status_code for i in range(6)]
    # same IP: 5 failures (20) + 5 distinct accounts (25) = medium on the 6th
    assert codes == [401] * 5 + [403]


async def test_automation_user_agent_adds_risk_but_does_not_block_alone(h: Harness):
    guard = install_guard(h, FakeChallenge())
    bot = await guard._assess(ctx(ua="python-requests/2.32"))
    empty = await guard._assess(ctx(ua=None))
    app = await guard._assess(ctx(ua=APP_UA))
    assert bot.score == 15 and bot.level is RiskLevel.LOW
    assert empty.score == 10 and empty.level is RiskLevel.LOW
    assert app.score == 0


# ================================================================ 6: challenge tokens


async def _to_medium(h: Harness, email: str) -> None:
    for _ in range(5):
        assert (await attempt(h, email)).status_code == 401


async def test_challenge_missing_invalid_expired_and_replayed(h: Harness, monkeypatch):
    challenge = FakeChallenge()
    install_guard(h, challenge)
    user = await register(h, verify=False)
    await _to_medium(h, user["email"])
    verifies = count_verifies(h, monkeypatch)

    missing = await attempt(h, user["email"], PASSWORD)
    assert missing.status_code == 403 and missing.json()["error"]["code"] == "challenge_required"
    for bad in ("garbage", "expired", "boom"):
        r = await attempt(h, user["email"], PASSWORD, token=bad)
        assert r.status_code == 403 and r.json()["error"]["code"] == "challenge_failed", bad
    assert verifies == []  # no password check without a passed challenge

    ok = await attempt(h, user["email"], PASSWORD, token="valid-once")
    assert ok.status_code == 200
    assert len(verifies) == 1  # exactly one password check, after the challenge passed


async def test_replayed_token_is_rejected_while_risk_is_medium(h: Harness):
    challenge = FakeChallenge()
    install_guard(h, challenge)
    await _to_medium(h, "replay@test.parkezy.dev")
    first = await attempt(h, "replay@test.parkezy.dev", token="valid-shared")
    assert first.status_code == 401  # challenge passed, password wrong
    second = await attempt(h, "replay@test.parkezy.dev", token="valid-shared")
    assert second.status_code == 403 and second.json()["error"]["code"] == "challenge_failed"
    assert challenge.calls.count("valid-shared") == 1


async def test_client_success_flag_is_never_trusted(h: Harness):
    install_guard(h, FakeChallenge())
    await _to_medium(h, "flag@test.parkezy.dev")
    r = await h.client.post(
        "/v1/auth/login",
        json={"email": "flag@test.parkezy.dev", "password": "x1234567", "captcha_passed": True, "success": True},
        headers={"user-agent": APP_UA},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "challenge_required"


async def test_without_a_provider_medium_risk_is_a_short_slowdown(h: Harness):
    install_guard(h)  # NoChallengeVerifier
    await _to_medium(h, "noprovider@test.parkezy.dev")
    r = await attempt(h, "noprovider@test.parkezy.dev")
    assert r.status_code == 429
    assert r.headers["retry-after"] == str(h.container.settings.login_challenge_unavailable_retry_seconds)


# ================================================================ 7: forwarding headers


async def test_spoofed_forwarded_for_first_hop_is_ignored_by_risk_scoring(h: Harness):
    install_guard(h, FakeChallenge())
    h.container.settings.trust_forwarded_for = True
    try:
        codes = []
        for i in range(6):
            # the client forges the first hop; the trusted proxy appends the real address last
            r = await attempt(h, f"spoof{i}@test.parkezy.dev", ip=f"6.6.{i}.6, 203.0.113.99")
            codes.append(r.status_code)
    finally:
        h.container.settings.trust_forwarded_for = False
    assert codes == [401] * 5 + [403]


async def test_forwarded_for_is_ignored_unless_trusted(h: Harness):
    install_guard(h, FakeChallenge())
    assert h.container.settings.trust_forwarded_for is False
    codes = [(await attempt(h, f"untrusted{i}@test.parkezy.dev", ip=f"9.9.{i}.9")).status_code for i in range(6)]
    assert codes == [401] * 5 + [403]  # all counted against the real peer address


# ================================================================ 8, 10: atomic counters, shared state


async def test_concurrent_failures_are_counted_exactly(h: Harness):
    guard = install_guard(h)
    target = ctx(email="race@test.parkezy.dev")
    await asyncio.gather(*(guard.record_failure(target) for _ in range(50)))
    assessment = await guard._assess(target)
    assert "account_failures=50" in " ".join(assessment.reasons)


async def test_concurrent_requests_respect_the_hard_ceiling_exactly(h: Harness, monkeypatch):
    monkeypatch.setattr(h.container.settings, "login_device_attempts_per_window", 10)
    guard = install_guard(h)
    target = ctx(device=device_id())

    async def one() -> bool:
        try:
            await guard.check(target, None)
            return True
        except RateLimited:
            return False

    results = await asyncio.gather(*(one() for _ in range(30)))
    assert results.count(True) == 10 and results.count(False) == 20


async def test_two_app_instances_share_rate_limit_state(h: Harness):
    second_redis = Redis.from_url(h.container.settings.redis_url)
    try:
        c = h.container
        instance_a = LoginProtection(c.settings, c.redis, c.one_time, FakeChallenge(), now=lambda: FIXED_NOW)
        instance_b = LoginProtection(c.settings, second_redis, c.one_time, FakeChallenge(), now=lambda: FIXED_NOW)
        target = ctx(email="shared@test.parkezy.dev")
        for _ in range(5):
            await instance_a.record_failure(target)
        assert (await instance_b._assess(target)).level is RiskLevel.MEDIUM
        with pytest.raises(ChallengeRequired):
            await instance_b.check(target, None)
    finally:
        await second_redis.aclose()


# ================================================================ 9: Redis unavailable or slow


async def test_redis_down_falls_back_to_local_limits_and_login_still_works(h: Harness, monkeypatch):
    dead = Redis.from_url("redis://127.0.0.1:1/0", socket_connect_timeout=0.2, socket_timeout=0.2)
    try:
        guard = install_guard(h, FakeChallenge(), redis=dead)
        user = await register(h, verify=False)
        r = await attempt(h, user["email"], PASSWORD)  # availability: real users still get in
        assert r.status_code == 200
        assessment = await guard._assess(ctx(email="x@test.parkezy.dev"))
        assert assessment.degraded and assessment.level is RiskLevel.LOW
        # recording never raises without Redis
        await guard.record_failure(ctx())
        await guard.record_success(ctx())
        # but a flood from one source is still cut off by the per-process fallback
        monkeypatch.setattr(h.container.settings, "login_fallback_attempts_per_window", 3)
        flood = ctx(email="flood@test.parkezy.dev", ip="198.51.100.200")
        outcomes = []
        for _ in range(5):
            try:
                await guard.check(flood, None)
                outcomes.append("ok")
            except RateLimited:
                outcomes.append("429")
        assert outcomes == ["ok", "ok", "ok", "429", "429"]
    finally:
        await dead.aclose()


async def test_redis_timeout_is_handled_like_an_outage(h: Harness, monkeypatch):
    guard = install_guard(h)

    async def slow(*args, **kwargs):
        raise RedisTimeoutError("Timeout reading from socket")

    monkeypatch.setattr("redis.asyncio.client.Pipeline.execute", slow)
    assessment = await guard._assess(ctx(email="slow@test.parkezy.dev"))
    assert assessment.degraded and assessment.level is RiskLevel.LOW


# ================================================================ 14: malformed input


async def test_malformed_and_oversized_login_requests(h: Harness):
    install_guard(h, FakeChallenge())
    post = h.client.post
    assert (await post("/v1/auth/login", json={"email": "a@test.parkezy.dev"})).status_code == 422
    assert (await post("/v1/auth/login", json={"email": "not-an-email", "password": "x"})).status_code == 422
    assert (
        await post("/v1/auth/login", json={"email": "a@test.parkezy.dev", "password": "x" * 129})
    ).status_code == 422
    long_token = {"email": "a@test.parkezy.dev", "password": "x", "challenge_token": "t" * 2049}
    assert (await post("/v1/auth/login", json=long_token)).status_code == 422
    r = await post("/v1/auth/login", content=b"{not json", headers={"content-type": "application/json"})
    assert r.status_code == 422
    big = h.container.settings.request_max_body_bytes + 1
    r = await post("/v1/auth/login", content=b"x" * big, headers={"content-type": "application/json"})
    assert r.status_code == 413
    # a malformed device header is ignored, not an error
    user = await register(h, verify=False)
    r = await attempt(h, user["email"], PASSWORD, device="not a valid id!")
    assert r.status_code == 200


async def test_security_events_contain_no_secrets(h: Harness, caplog):
    install_guard(h, FakeChallenge())
    user = await register(h, verify=False)
    with caplog.at_level("INFO", logger="parkezy.security"):
        await attempt(h, user["email"], "Secret-Guess-123")
        await attempt(h, user["email"], PASSWORD)
    events = [r.security for r in caplog.records if hasattr(r, "security")]
    names = {e["event"] for e in events}
    assert {"login_risk", "login_failure", "login_success"} <= names
    text = repr(events)
    assert user["email"] not in text and "Secret-Guess-123" not in text and PASSWORD not in text
    assert "127.0.0.1" not in text


async def test_many_real_users_behind_one_nat_are_not_challenged(h: Harness):
    """Campus Wi-Fi / carrier NAT: one IP, many different people signing in successfully."""
    install_guard(h, FakeChallenge())
    users = [await register(h, verify=False) for _ in range(12)]
    codes = [(await attempt(h, u["email"], PASSWORD)).status_code for u in users]
    assert codes == [200] * 12
