import asyncio
import hashlib
import hmac
import secrets
import uuid
import weakref
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.clock import Clock
from app.core.errors import Unauthorized


class PasswordHasher:
    """argon2id with argon2-cffi's default (RFC 9106 low-memory) parameters.

    Hashing is deliberately expensive (~70 ms CPU, 64 MiB RAM). The async methods run it in a
    thread (argon2-cffi releases the GIL) so the event loop keeps serving other requests, and a
    per-event-loop semaphore caps how many hashes run at once: memory stays bounded, and a burst of
    sign-ins queues up here instead of starving everything else. The sync methods remain for
    scripts and are identical in output.
    """

    def __init__(self, max_concurrency: int = 2) -> None:
        self._argon = _Argon2()
        self._max_concurrency = max_concurrency
        self._semaphores: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
            weakref.WeakKeyDictionary()
        )

    def hash(self, password: str) -> str:
        return self._argon.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._argon.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def _semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        sem = self._semaphores.get(loop)
        if sem is None:
            sem = self._semaphores[loop] = asyncio.Semaphore(self._max_concurrency)
        return sem

    async def hash_async(self, password: str) -> str:
        async with self._semaphore():
            return await asyncio.to_thread(self.hash, password)

    async def verify_async(self, password_hash: str, password: str) -> bool:
        async with self._semaphore():
            return await asyncio.to_thread(self.verify, password_hash, password)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._argon.check_needs_rehash(password_hash)


class TokenService:
    """Signs and verifies short-lived JWTs (API access tokens and parking QR tokens).

    Expiry is checked against the injected Clock (not the wall clock inside PyJWT) so time is
    consistent across the whole application and testable."""

    def __init__(self, secret: str, algorithm: str, issuer: str, audience: str, clock: Clock) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._clock = clock

    def encode(self, subject: str, purpose: str, now: datetime, ttl: timedelta, **extra) -> str:
        payload = {
            "sub": subject,
            "pur": purpose,
            "iss": self._issuer,
            "aud": self._audience,
            "iat": int(now.timestamp()),
            "exp": int((now + ttl).timestamp()),
            "jti": uuid.uuid4().hex,
            **extra,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str, purpose: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={"verify_exp": False, "verify_iat": False, "require": ["exp", "sub", "jti"]},
            )
        except jwt.PyJWTError as e:
            raise Unauthorized("Invalid token", code="token_invalid") from e
        if payload.get("pur") != purpose:
            raise Unauthorized("Invalid token", code="token_invalid")
        if payload["exp"] <= self._clock.now().timestamp():
            raise Unauthorized("Token expired", code="token_expired")
        return payload


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_digits(length: int) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hmac_hex(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
