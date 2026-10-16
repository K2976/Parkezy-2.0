"""Sign in with Google / Apple: verify the provider's ID token (an OpenID Connect JWT).

The app gets the ID token from the provider's native SDK and sends it to us. We check the
signature against the provider's published keys (JWKS), the issuer, the audience (our client
ids), expiry and, when the app used one, the nonce. Tests replace this port with a fake.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Protocol

import httpx
import jwt

from app.core.errors import ExternalServiceError, ServiceUnavailable, Unauthorized

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SocialIdentity:
    subject: str
    email: str | None
    email_verified: bool
    full_name: str | None


class IdentityVerifier(Protocol):
    async def verify(self, *, provider: str, id_token: str, nonce: str | None) -> SocialIdentity: ...


@dataclass(frozen=True)
class ProviderConfig:
    issuers: tuple[str, ...]
    jwks_url: str
    client_ids: tuple[str, ...]


GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_ISSUERS = ("https://appleid.apple.com",)
APPLE_JWKS = "https://appleid.apple.com/auth/keys"
CLERK_ISSUERS = ("https://exciting-sawfly-3079.clerk.accounts.dev",)
CLERK_JWKS = "https://exciting-sawfly-3079.clerk.accounts.dev/.well-known/jwks.json"
JWKS_TTL_SECONDS = 3600


def _truthy(value: object) -> bool:
    # Apple sends booleans as strings ("true").
    return value is True or (isinstance(value, str) and value.lower() == "true")


class OidcIdentityVerifier:
    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        google_client_ids: list[str],
        apple_client_ids: list[str],
        clerk_issuer: str = "https://exciting-sawfly-3079.clerk.accounts.dev",
        clerk_jwks_url: str = "https://exciting-sawfly-3079.clerk.accounts.dev/.well-known/jwks.json",
    ) -> None:
        self._http = http
        self._providers = {
            "google": ProviderConfig(GOOGLE_ISSUERS, GOOGLE_JWKS, tuple(google_client_ids)),
            "apple": ProviderConfig(APPLE_ISSUERS, APPLE_JWKS, tuple(apple_client_ids)),
            "clerk": ProviderConfig((clerk_issuer,), clerk_jwks_url, ()),
        }
        self._jwks: dict[str, tuple[float, dict[str, jwt.PyJWK]]] = {}

    async def _keys(self, url: str, *, force: bool = False) -> dict[str, jwt.PyJWK]:
        cached = self._jwks.get(url)
        if cached and not force and time.monotonic() - cached[0] < JWKS_TTL_SECONDS:
            return cached[1]
        try:
            response = await self._http.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ExternalServiceError("Could not reach the sign-in provider") from e
        keys = {k["kid"]: jwt.PyJWK(k) for k in response.json().get("keys", []) if "kid" in k}
        self._jwks[url] = (time.monotonic(), keys)
        return keys

    async def verify(self, *, provider: str, id_token: str, nonce: str | None) -> SocialIdentity:
        config = self._providers.get(provider)
        if config is None or (provider != "clerk" and not config.client_ids):
            raise ServiceUnavailable(f"Sign in with {provider.title()} is not set up", code="provider_not_configured")
        invalid = Unauthorized("Could not verify the sign-in, please try again", code="invalid_id_token")
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
        except jwt.PyJWTError as e:
            raise invalid from e
        keys = await self._keys(config.jwks_url)
        if kid not in keys:  # keys rotate; refetch once before giving up
            keys = await self._keys(config.jwks_url, force=True)
        key = keys.get(kid) if isinstance(kid, str) else None
        if key is None:
            raise invalid
        try:
            options = {"require": ["exp", "iat", "sub", "iss"]}
            audience = list(config.client_ids) if config.client_ids else None
            if audience:
                options["require"].append("aud")
            else:
                options["verify_aud"] = False

            claims = jwt.decode(
                id_token,
                key.key,
                algorithms=["RS256", "ES256"],
                audience=audience,
                issuer=list(config.issuers),
                options=options,
            )
        except jwt.PyJWTError as e:
            log.info("rejected %s id token: %s", provider, e)
            raise invalid from e
        if nonce is not None:
            token_nonce = claims.get("nonce")
            # Apple's SDK sends sha256(nonce) to Apple; Google echoes it as-is. Accept either.
            if token_nonce not in (nonce, hashlib.sha256(nonce.encode()).hexdigest()):
                raise invalid
        email = claims.get("email")
        if not email and claims.get("email_addresses"):
            emails = claims.get("email_addresses")
            if isinstance(emails, list) and emails and isinstance(emails[0], dict):
                email = emails[0].get("email_address")
        full_name = claims.get("name") or claims.get("full_name")
        if not full_name and (claims.get("given_name") or claims.get("family_name")):
            full_name = f"{claims.get('given_name', '')} {claims.get('family_name', '')}".strip()

        return SocialIdentity(
            subject=str(claims["sub"]),
            email=email.lower() if isinstance(email, str) else None,
            email_verified=_truthy(claims.get("email_verified", True)),
            full_name=full_name or None,
        )
