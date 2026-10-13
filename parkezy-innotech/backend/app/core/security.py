import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.clock import Clock
from app.core.errors import Unauthorized


class PasswordHasher:
    def __init__(self) -> None:
        self._argon = _Argon2()

    def hash(self, password: str) -> str:
        return self._argon.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._argon.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

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
