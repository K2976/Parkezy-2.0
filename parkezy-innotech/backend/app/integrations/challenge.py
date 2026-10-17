"""Login challenges (CAPTCHA), verified server-side with the provider.

The client only ever sends the opaque token the widget produced; a "success" flag from the client
is never trusted. Verification fails closed: a provider outage means the challenge is not passed.
Replay of a token is blocked separately (LoginProtection keeps a one-time registry), on top of the
provider's own single-use check.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx

log = logging.getLogger(__name__)

MAX_TOKEN_LENGTH = 2048  # Turnstile tokens are ~1-2 KB; anything longer is not a real token


@dataclass(frozen=True)
class ChallengeResult:
    ok: bool
    reason: str  # internal (logs/metrics), never sent to the client


class ChallengeVerifier(Protocol):
    provider: str
    site_key: str | None

    async def verify(self, token: str, remote_ip: str | None) -> ChallengeResult: ...


class NoChallengeVerifier:
    """No provider configured: nothing can pass a challenge (LoginProtection slows down instead)."""

    provider = "none"
    site_key: str | None = None

    async def verify(self, token: str, remote_ip: str | None) -> ChallengeResult:
        return ChallengeResult(False, "no_provider")


class TurnstileVerifier:
    """Cloudflare Turnstile siteverify (https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)."""

    provider = "turnstile"

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        verify_url: str,
        secret_key: str,
        site_key: str,
        expected_hostnames: list[str],
        expected_action: str | None,
        max_age_seconds: int,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._http = http
        self._verify_url = verify_url
        self._secret_key = secret_key
        self.site_key: str | None = site_key
        self._hostnames = set(expected_hostnames)
        self._action = expected_action
        self._max_age = max_age_seconds
        self._now = now

    async def verify(self, token: str, remote_ip: str | None) -> ChallengeResult:
        if not token or len(token) > MAX_TOKEN_LENGTH:
            return ChallengeResult(False, "malformed_token")
        form = {"secret": self._secret_key, "response": token}
        if remote_ip:
            form["remoteip"] = remote_ip
        try:
            response = await self._http.post(self._verify_url, data=form)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            log.warning("turnstile verification unavailable", exc_info=True)
            return ChallengeResult(False, "provider_unavailable")
        if not isinstance(data, dict) or data.get("success") is not True:
            codes = data.get("error-codes", []) if isinstance(data, dict) else []
            return ChallengeResult(False, "rejected:" + ",".join(map(str, codes))[:100])
        if self._hostnames and data.get("hostname") not in self._hostnames:
            return ChallengeResult(False, "hostname_mismatch")
        if self._action and data.get("action") != self._action:
            return ChallengeResult(False, "action_mismatch")
        try:
            issued = datetime.fromisoformat(str(data["challenge_ts"]).replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            return ChallengeResult(False, "missing_timestamp")
        if self._now() - issued > self._max_age:
            return ChallengeResult(False, "expired")
        return ChallengeResult(True, "ok")
