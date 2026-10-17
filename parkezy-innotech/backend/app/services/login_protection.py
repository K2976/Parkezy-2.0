"""Adaptive login abuse protection: a cheap risk check that runs BEFORE the expensive argon2 verify.

Per login request:

1. `check()` does ONE atomic Redis round trip (MULTI/EXEC) that counts this attempt in the hard
   ceilings (per subnet, per device, service-wide), reads the recent failure counters (per account,
   IP, subnet, device, service-wide), reads two HyperLogLogs of failures (distinct accounts failing
   from this IP, distinct IPs failing on this account) and checks whether this device signed in to this account before.
2. The signals are scored with configurable rules (`score()`, a pure function) into LOW / MEDIUM /
   HIGH. LOW continues; MEDIUM requires a solved challenge (CAPTCHA), or a short slow-down when no
   provider is configured; HIGH is a temporary 429. Nothing is permanent: every counter expires.
3. The caller verifies the password only when `check()` returned, then reports the result with
   `record_failure()` / `record_success()` (one more round trip).

Privacy: emails, IPs and device ids are only stored as truncated HMACs, in keys that expire.
Account enumeration: nothing here depends on whether the account exists; failures against unknown
emails are counted exactly like wrong passwords. Clients never see scores or reasons.
If Redis is unreachable, a small per-process fallback still limits attempts per IP and per account.
"""

import hashlib
import ipaddress
import logging
import math
import re
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import RiskRule, Settings
from app.core.errors import ChallengeRequired, RateLimited
from app.core.security import hmac_hex
from app.infra import metrics
from app.infra.one_time import OneTimeTokenRegistry
from app.integrations.challenge import ChallengeResult, ChallengeVerifier

log = logging.getLogger("parkezy.security")

THROTTLED_MESSAGE = "Too many sign-in attempts, please try again later"
DEVICE_ID = re.compile(r"[A-Za-z0-9_-]{16,128}")
# Scripted HTTP clients and headless browsers. The real app sends okhttp (Android) / CFNetwork (iOS),
# which are deliberately not listed. A match only adds a few points; it never blocks on its own.
AUTOMATION_UA = re.compile(
    r"curl|wget|python-requests|python-urllib|aiohttp|httpx|go-http-client|libwww|scrapy|headless|"
    r"phantomjs|selenium|puppeteer|playwright|apache-httpclient|node-fetch|axios",
    re.IGNORECASE,
)


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class LoginContext:
    ip: str
    email: str
    device_id: str | None
    user_agent: str | None

    @classmethod
    def build(cls, *, ip: str, email: str, device_header: str | None, user_agent: str | None) -> "LoginContext":
        device = device_header if device_header and DEVICE_ID.fullmatch(device_header) else None
        return cls(ip=ip, email=email.strip().lower(), device_id=device, user_agent=(user_agent or "").strip() or None)


@dataclass(frozen=True)
class Signals:
    """Field names match the keys of the risk rules (config.DEFAULT_LOGIN_RISK_RULES)."""

    account_failures: int = 0
    ip_failures: int = 0
    subnet_failures: int = 0
    device_failures: int = 0
    ip_distinct_accounts: int = 0
    account_distinct_ips: int = 0
    global_failures: int = 0
    automation_user_agent: bool = False
    missing_user_agent: bool = False
    known_device: bool = False


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    score: int
    reasons: tuple[str, ...]  # internal only: logs and tests
    degraded: bool = False


def score(
    signals: Signals, rules: dict[str, RiskRule], medium: int, high: int, *, degraded: bool = False
) -> RiskAssessment:
    """Deterministic: each rule adds weight * min(cap, value // threshold); total is floored at 0."""
    total = 0
    reasons: list[str] = []
    for name, rule in rules.items():
        value = int(getattr(signals, name))
        steps = min(rule.cap, value // rule.threshold)
        if steps:
            points = rule.weight * steps
            total += points
            reasons.append(f"{name}={value}:{points:+d}")
    total = max(0, total)
    level = RiskLevel.HIGH if total >= high else RiskLevel.MEDIUM if total >= medium else RiskLevel.LOW
    return RiskAssessment(level, total, tuple(reasons), degraded)


def subnet_of(ip: str) -> str:
    """/24 for IPv4, /64 for IPv6 (one home or one mobile carrier allocation)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    return str(ipaddress.ip_network(f"{addr}/{24 if addr.version == 4 else 64}", strict=False))


@dataclass(frozen=True)
class _Window:
    """Sliding-window-counter keys (same estimate as app.infra.rate_limit.RateLimiter)."""

    current: str
    previous: str
    seconds: int
    overlap: float  # weight of the previous window still inside the rolling window

    @classmethod
    def at(cls, base: str, seconds: int, now: float) -> "_Window":
        index = int(now // seconds)
        return cls(f"{base}:{index}", f"{base}:{index - 1}", seconds, 1 - (now % seconds) / seconds)

    def estimate(self, current: Any, previous: Any) -> int:
        return math.floor(int(current or 0) + int(previous or 0) * self.overlap)

    def retry_after(self, now: float) -> int:
        return max(1, math.ceil(self.seconds - now % self.seconds))


class _LocalFallback:
    """Per-process fixed-window counters, used only while Redis is unreachable. Bounded in size."""

    def __init__(self, max_keys: int = 20_000) -> None:
        self._counts: OrderedDict[str, int] = OrderedDict()
        self._window: int | None = None
        self._max_keys = max_keys

    def hit(self, keys: list[str], window: int) -> int:
        if window != self._window:
            self._counts.clear()
            self._window = window
        highest = 0
        for key in keys:
            count = self._counts.pop(key, 0) + 1
            self._counts[key] = count
            highest = max(highest, count)
            if len(self._counts) > self._max_keys:
                self._counts.popitem(last=False)
        return highest


class LoginProtection:
    def __init__(
        self,
        settings: Settings,
        redis: Redis,
        one_time: OneTimeTokenRegistry,
        challenge: ChallengeVerifier,
        *,
        now: Callable[[], float] = time.time,
        prefix: str = "lp",
    ) -> None:
        self._settings = settings
        self._redis = redis
        self._one_time = one_time
        self.challenge = challenge
        self._now = now
        self._prefix = prefix
        self._fallback = _LocalFallback()

    # ------------------------------------------------------------ keys
    def _id(self, kind: str, value: str) -> str:
        secret = self._settings.jwt_secret.get_secret_value()
        return hmac_hex(secret, f"login-protection:{kind}:{value}")[:32]

    def _ids(self, ctx: LoginContext) -> dict[str, str | None]:
        return {
            "account": self._id("account", ctx.email),
            "ip": self._id("ip", ctx.ip),
            "subnet": self._id("subnet", subnet_of(ctx.ip)),
            "device": self._id("device", ctx.device_id) if ctx.device_id else None,
        }

    def _key(self, *parts: str) -> str:
        return ":".join((self._prefix, *parts))

    def _spread_keys(self, ids: dict[str, str | None], now: float) -> tuple[list[str], list[str]]:
        """HyperLogLogs of FAILED attempts only (current + previous window): accounts that failed from
        this IP, and IPs that failed on this account. Successful sign-ins never count, so many real
        users behind one NAT (campus Wi-Fi, carrier-grade NAT) do not look like credential stuffing."""
        index = int(now // self._settings.login_failure_window_seconds)
        ip_accounts = [self._key("ipacc", str(ids["ip"]), str(index - n)) for n in (0, 1)]
        account_ips = [self._key("accip", str(ids["account"]), str(index - n)) for n in (0, 1)]
        return ip_accounts, account_ips

    # ------------------------------------------------------------ public API
    async def check(self, ctx: LoginContext, challenge_token: str | None) -> RiskAssessment:
        """Raise RateLimited / ChallengeRequired, or return when the password may be verified."""
        s = self._settings
        if not s.login_protection_enabled:
            return RiskAssessment(RiskLevel.LOW, 0, ("disabled",))
        assessment = await self._assess(ctx)
        metrics.LOGIN_RISK.labels(assessment.level.value).inc()
        self._event(
            "login_risk",
            ctx,
            logging.INFO if assessment.level is RiskLevel.LOW else logging.WARNING,
            level=assessment.level.value,
            score=assessment.score,
            reasons=list(assessment.reasons),
            degraded=assessment.degraded,
        )
        if assessment.level is RiskLevel.HIGH:
            self._reject(ctx, "high_risk", s.login_throttle_retry_seconds)
        if assessment.level is RiskLevel.MEDIUM:
            await self._require_challenge(ctx, challenge_token)
        return assessment

    async def record_failure(self, ctx: LoginContext) -> None:
        s = self._settings
        ids, now = self._ids(ctx), self._now()
        windows = [
            _Window.at(self._key("fail", kind, ident), s.login_failure_window_seconds, now)
            for kind, ident in ids.items()
            if ident
        ]
        global_window = _Window.at(self._key("fail", "global"), s.rate_limit_window_seconds, now)
        ip_accounts, account_ips = self._spread_keys(ids, now)
        try:
            pipe = self._redis.pipeline(transaction=True)
            pipe.pfadd(ip_accounts[0], str(ids["account"]))
            pipe.expire(ip_accounts[0], s.login_failure_window_seconds * 2)
            pipe.pfadd(account_ips[0], str(ids["ip"]))
            pipe.expire(account_ips[0], s.login_failure_window_seconds * 2)
            for w in [*windows, global_window]:
                pipe.incr(w.current)
                pipe.expire(w.current, w.seconds * 2)
            pipe.get(global_window.previous)
            results = await pipe.execute()
            global_failures = global_window.estimate(results[-3], results[-1])
            spike_threshold = s.effective_login_risk_rules["global_failures"].threshold
            # One alert per window when service-wide failures cross the attack threshold.
            if global_failures >= spike_threshold and await self._redis.set(
                self._key("spike", global_window.current.rsplit(":", 1)[-1]), 1, nx=True, ex=global_window.seconds * 2
            ):
                self._event("login_failure_spike", None, logging.WARNING, failures=global_failures)
        except RedisError:
            log.warning("login protection could not record a failure", exc_info=True)
        metrics.LOGIN_ATTEMPTS.labels("invalid_credentials").inc()
        self._event("login_failure", ctx, logging.INFO)

    async def record_success(self, ctx: LoginContext) -> None:
        s = self._settings
        ids, now = self._ids(ctx), self._now()
        account = _Window.at(self._key("fail", "account", ids["account"] or ""), s.login_failure_window_seconds, now)
        try:
            pipe = self._redis.pipeline(transaction=True)
            # The owner got in: forget this account's recent failures (IP/subnet counters stay).
            pipe.delete(account.current, account.previous)
            if ids["device"]:
                known = self._key("known", ids["account"] or "")
                pipe.sadd(known, ids["device"])
                pipe.expire(known, s.login_known_device_ttl_days * 86_400)
            await pipe.execute()
        except RedisError:
            log.warning("login protection could not record a success", exc_info=True)
        metrics.LOGIN_ATTEMPTS.labels("success").inc()
        self._event("login_success", ctx, logging.INFO)

    # ------------------------------------------------------------ internals
    async def _assess(self, ctx: LoginContext) -> RiskAssessment:
        s = self._settings
        rules = s.effective_login_risk_rules
        ids, now = self._ids(ctx), self._now()
        rate_w, fail_w = s.rate_limit_window_seconds, s.login_failure_window_seconds
        ceilings = [
            ("subnet", ids["subnet"], s.login_subnet_attempts_per_window),
            ("global", "all", s.login_global_attempts_per_window),
        ]
        if ids["device"]:
            ceilings.append(("device", ids["device"], s.login_device_attempts_per_window))
        attempt_windows = [(_Window.at(self._key("try", k, str(i)), rate_w, now), limit) for k, i, limit in ceilings]
        fail_windows = {
            kind: _Window.at(self._key("fail", kind, ident), fail_w, now) for kind, ident in ids.items() if ident
        }
        global_fail = _Window.at(self._key("fail", "global"), rate_w, now)
        ip_accounts, account_ips = self._spread_keys(ids, now)
        try:
            pipe = self._redis.pipeline(transaction=True)
            for w, _ in attempt_windows:
                pipe.incr(w.current)
                pipe.expire(w.current, w.seconds * 2)
                pipe.get(w.previous)
            for w in [*fail_windows.values(), global_fail]:
                pipe.get(w.current)
                pipe.get(w.previous)
            pipe.pfcount(*ip_accounts)
            pipe.pfcount(*account_ips)
            if ids["device"]:
                pipe.sismember(self._key("known", ids["account"] or ""), ids["device"])
            results = list(await pipe.execute())
        except RedisError:
            return self._fallback_assessment(ctx, ids, now)

        for w, limit in attempt_windows:
            current, _, previous = results[:3]
            del results[:3]
            if w.estimate(current, previous) > limit:
                self._reject(ctx, "hard_limit", w.retry_after(now), outcome="rate_limited")
        failures = {}
        for kind, w in [*fail_windows.items(), ("global", global_fail)]:
            failures[kind] = w.estimate(results[0], results[1])
            del results[:2]
        ip_distinct_accounts, account_distinct_ips = int(results[0]), int(results[1])
        known_device = bool(results[2]) if ids["device"] else False
        user_agent = ctx.user_agent or ""
        signals = Signals(
            account_failures=failures["account"],
            ip_failures=failures["ip"],
            subnet_failures=failures["subnet"],
            device_failures=failures.get("device", 0),
            ip_distinct_accounts=ip_distinct_accounts,
            account_distinct_ips=account_distinct_ips,
            global_failures=failures["global"],
            automation_user_agent=bool(AUTOMATION_UA.search(user_agent)),
            missing_user_agent=not user_agent,
            known_device=known_device,
        )
        return score(signals, rules, s.login_risk_medium_score, s.login_risk_high_score)

    def _fallback_assessment(self, ctx: LoginContext, ids: dict[str, str | None], now: float) -> RiskAssessment:
        s = self._settings
        log.warning("login protection running without Redis (per-process fallback)", exc_info=True)
        metrics.LOGIN_PROTECTION_DEGRADED.inc()
        window = int(now // s.rate_limit_window_seconds)
        count = self._fallback.hit([f"ip:{ids['ip']}", f"account:{ids['account']}"], window)
        if count > s.login_fallback_attempts_per_window:
            return RiskAssessment(RiskLevel.HIGH, s.login_risk_high_score, (f"fallback_attempts={count}",), True)
        return RiskAssessment(RiskLevel.LOW, 0, ("fallback",), True)

    async def _require_challenge(self, ctx: LoginContext, token: str | None) -> None:
        s = self._settings
        if self.challenge.provider == "none":
            # No CAPTCHA configured: slow down instead (the user can retry shortly; nothing is locked).
            self._reject(ctx, "challenge_unavailable", s.login_challenge_unavailable_retry_seconds)
        details = {"provider": self.challenge.provider, "site_key": self.challenge.site_key}
        if not token:
            metrics.LOGIN_ATTEMPTS.labels("challenged").inc()
            self._event("login_challenge_required", ctx, logging.INFO)
            raise ChallengeRequired("Please complete the verification to continue", details=details)
        token_id = hashlib.sha256(token.encode()).hexdigest()
        try:
            fresh = await self._one_time.consume("login-challenge", token_id, s.login_challenge_max_age_seconds)
        except RedisError:
            fresh = True  # the provider's own single-use check still applies
        result: ChallengeResult | None = None
        if fresh:
            try:
                result = await self.challenge.verify(token, ctx.ip)
            except Exception:  # noqa: BLE001 - a broken provider client must fail closed, not 500
                log.exception("challenge verifier error")
                result = ChallengeResult(False, "verifier_error")
        if result is None or not result.ok:
            reason = "replayed" if result is None else result.reason
            metrics.LOGIN_CHALLENGES.labels("replayed" if result is None else "failed").inc()
            metrics.LOGIN_ATTEMPTS.labels("challenge_failed").inc()
            self._event("login_challenge_failed", ctx, logging.WARNING, reason=reason)
            raise ChallengeRequired("Verification failed, please try again", code="challenge_failed", details=details)
        metrics.LOGIN_CHALLENGES.labels("passed").inc()
        self._event("login_challenge_passed", ctx, logging.INFO)

    def _reject(self, ctx: LoginContext, reason: str, retry_after: int, *, outcome: str = "throttled") -> None:
        metrics.LOGIN_ATTEMPTS.labels(outcome).inc()
        self._event("login_rejected", ctx, logging.WARNING, reason=reason, retry_after_seconds=retry_after)
        raise RateLimited(THROTTLED_MESSAGE, details={"retry_after_seconds": retry_after})

    def _event(self, name: str, ctx: LoginContext | None, severity: int, **fields: object) -> None:
        """Structured security event. Pseudonymous ids only: no email, IP, password or token."""
        if ctx is not None:
            fields = {
                "account": self._id("account", ctx.email)[:12],
                "ip": self._id("ip", ctx.ip)[:12],
                "device": bool(ctx.device_id),
                **fields,
            }
        log.log(severity, name, extra={"security": {"event": name, **fields}})
