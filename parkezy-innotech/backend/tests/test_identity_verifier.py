"""The real Google/Apple ID-token verifier, against a locally generated signing key served as JWKS.

The end-to-end sign-in tests (test_social_auth.py) use a fake verifier; these make sure the real one
checks signature, issuer, audience, expiry and nonce, and refetches keys when the provider rotates them."""

import hashlib
import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.errors import ServiceUnavailable, Unauthorized
from app.integrations.identity import APPLE_JWKS, GOOGLE_JWKS, OidcIdentityVerifier

CLIENT = "parkezy-ios.apps.googleusercontent.com"


def _key(kid: str):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    return private, jwk | {"kid": kid, "alg": "RS256", "use": "sig"}


def _token(private, kid: str, **claims) -> str:
    now = int(time.time())
    body = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT,
        "sub": "google-123",
        "email": "Asha@Example.com",
        "email_verified": True,
        "name": "Asha Rao",
        "iat": now,
        "exp": now + 600,
    } | claims
    return jwt.encode(body, private, algorithm="RS256", headers={"kid": kid})


class Jwks:
    def __init__(self, *keys: dict) -> None:
        self.keys = list(keys)
        self.fetches = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert str(request.url) in (GOOGLE_JWKS, APPLE_JWKS)
        self.fetches += 1
        return httpx.Response(200, json={"keys": self.keys})


def _verifier(jwks: Jwks, google=(CLIENT,), apple=("dev.parkezy.app",)) -> OidcIdentityVerifier:
    client = httpx.AsyncClient(transport=httpx.MockTransport(jwks.handler))
    return OidcIdentityVerifier(client, google_client_ids=list(google), apple_client_ids=list(apple))


async def test_valid_google_token():
    private, jwk = _key("k1")
    v = _verifier(Jwks(jwk))
    identity = await v.verify(provider="google", id_token=_token(private, "k1"), nonce=None)
    assert (identity.subject, identity.email, identity.email_verified, identity.full_name) == (
        "google-123",
        "asha@example.com",
        True,
        "Asha Rao",
    )


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "someone-elses-app"},
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 60},
    ],
)
async def test_rejects_wrong_audience_issuer_or_expired(claims):
    private, jwk = _key("k1")
    v = _verifier(Jwks(jwk))
    with pytest.raises(Unauthorized) as e:
        await v.verify(provider="google", id_token=_token(private, "k1", **claims), nonce=None)
    assert e.value.code == "invalid_id_token"


async def test_rejects_token_signed_by_another_key():
    _, jwk = _key("k1")
    attacker, _ = _key("k1")  # same kid, different private key
    v = _verifier(Jwks(jwk))
    with pytest.raises(Unauthorized):
        await v.verify(provider="google", id_token=_token(attacker, "k1"), nonce=None)


async def test_rejects_garbage_and_unknown_key():
    private, jwk = _key("k1")
    jwks = Jwks(jwk)
    v = _verifier(jwks)
    with pytest.raises(Unauthorized):
        await v.verify(provider="google", id_token="not-a-jwt", nonce=None)
    with pytest.raises(Unauthorized):
        await v.verify(provider="google", id_token=_token(private, "unknown-kid"), nonce=None)


async def test_refetches_keys_after_rotation():
    old_private, old_jwk = _key("old")
    new_private, new_jwk = _key("new")
    jwks = Jwks(old_jwk)
    v = _verifier(jwks)
    await v.verify(provider="google", id_token=_token(old_private, "old"), nonce=None)
    assert jwks.fetches == 1
    await v.verify(provider="google", id_token=_token(old_private, "old"), nonce=None)
    assert jwks.fetches == 1  # cached
    jwks.keys = [new_jwk]  # the provider rotated its keys
    identity = await v.verify(provider="google", id_token=_token(new_private, "new"), nonce=None)
    assert identity.subject == "google-123" and jwks.fetches == 2


async def test_apple_nonce_is_hashed_and_email_verified_may_be_a_string():
    private, jwk = _key("a1")
    v = _verifier(Jwks(jwk))
    raw = "random-nonce-123"
    token = _token(
        private,
        "a1",
        iss="https://appleid.apple.com",
        aud="dev.parkezy.app",
        nonce=hashlib.sha256(raw.encode()).hexdigest(),
        email_verified="true",
        name=None,
    )
    identity = await v.verify(provider="apple", id_token=token, nonce=raw)
    assert identity.email_verified is True and identity.full_name is None
    with pytest.raises(Unauthorized):
        await v.verify(provider="apple", id_token=token, nonce="a-different-nonce")


async def test_a_google_token_is_not_an_apple_token():
    private, jwk = _key("k1")
    v = _verifier(Jwks(jwk))
    with pytest.raises(Unauthorized):
        await v.verify(provider="apple", id_token=_token(private, "k1"), nonce=None)


async def test_unconfigured_provider_is_unavailable():
    private, jwk = _key("k1")
    v = _verifier(Jwks(jwk), google=())
    with pytest.raises(ServiceUnavailable) as e:
        await v.verify(provider="google", id_token=_token(private, "k1"), nonce=None)
    assert e.value.code == "provider_not_configured"
