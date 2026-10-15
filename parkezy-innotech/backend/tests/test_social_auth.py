"""Sign in with Google / Apple.

Contract
--------
POST /v1/auth/social  body {provider: "google"|"apple", id_token, nonce?, full_name?}
     -> 201 AuthOut for a new account, 200 AuthOut for an existing one ({user, tokens} like /register).

Token verification is a port on the container: `container.identity_verifier` with
    async verify(*, provider: str, id_token: str, nonce: str | None) -> identity
where identity has `subject`, `email` (may be None for Apple after the first sign-in),
`email_verified` and `full_name`. It raises Unauthorized(code="invalid_id_token") for bad tokens.
Tests swap in a fake, exactly like the email/push/payment fakes in conftest.

Rules
-----
* Look up by (provider, subject) first - a changed provider email still finds the same account.
* Otherwise link to an existing account with the same email (case-insensitive), only if the provider
  says the email is verified. If that existing account was *never verified*, its password is cleared
  and its sessions revoked (it may have been pre-registered by someone else) - prevents takeover.
* Provider email not verified -> 403 `provider_email_unverified`.
* First sign-in with no email (Apple hides it) -> 422 `email_required`.
* New accounts are email_verified and have no password; Apple's name comes from the request body.
* Suspended/deleted accounts cannot sign in (401); after deletion the same identity creates a new account.
* Password-less accounts: password login fails (401 `invalid_credentials`), change-password -> 409
  `no_password`, and DELETE /v1/me accepts an empty body.
"""

from dataclasses import dataclass

import pytest

from app.core.errors import Unauthorized
from tests.conftest import Harness
from tests.helpers import auth, register


@dataclass
class Identity:
    subject: str
    email: str | None
    email_verified: bool = True
    full_name: str | None = None


class FakeIdentityVerifier:
    def __init__(self) -> None:
        self.tokens: dict[tuple[str, str], Identity] = {}
        self.calls: list[dict] = []

    def issue(self, provider: str, token: str, identity: Identity) -> None:
        self.tokens[(provider, token)] = identity

    async def verify(self, *, provider: str, id_token: str, nonce: str | None = None) -> Identity:
        self.calls.append({"provider": provider, "id_token": id_token, "nonce": nonce})
        try:
            return self.tokens[(provider, id_token)]
        except KeyError:
            raise Unauthorized("Could not verify the sign-in", code="invalid_id_token") from None


@pytest.fixture
def idp(h: Harness) -> FakeIdentityVerifier:
    fake = FakeIdentityVerifier()
    h.container.identity_verifier = fake
    return fake


async def _social(h: Harness, provider: str, token: str, **extra):
    return await h.client.post("/v1/auth/social", json={"provider": provider, "id_token": token} | extra)


async def test_new_google_user_then_returning_user(h: Harness, idp: FakeIdentityVerifier):
    idp.issue("google", "g1", Identity("google-sub-1", "Asha@Example.com", True, "Asha Rao"))
    r = await _social(h, "google", "g1")
    assert r.status_code == 201, r.text
    data = r.json()
    user = data["user"]
    assert user["email"].lower() == "asha@example.com" and user["email_verified"] is True
    assert user["full_name"] == "Asha Rao" and user["is_host"] is False
    token = data["tokens"]["access_token"]
    assert (await h.client.get("/v1/me", headers=auth(token))).json()["id"] == user["id"]

    r = await _social(h, "google", "g1")
    assert r.status_code == 200 and r.json()["user"]["id"] == user["id"], r.text

    # The refresh token from a social sign-in works like any other.
    r = await h.client.post("/v1/auth/refresh", json={"refresh_token": data["tokens"]["refresh_token"]})
    assert r.status_code == 200, r.text


async def test_lookup_is_by_subject_not_email(h: Harness, idp: FakeIdentityVerifier):
    idp.issue("google", "g1", Identity("sub-x", "old@example.com"))
    first = (await _social(h, "google", "g1")).json()["user"]
    idp.issue("google", "g2", Identity("sub-x", "new@example.com"))  # user changed their Google email
    r = await _social(h, "google", "g2")
    assert r.status_code == 200 and r.json()["user"]["id"] == first["id"], r.text


async def test_apple_name_comes_from_request_and_email_only_on_first_sign_in(h: Harness, idp: FakeIdentityVerifier):
    idp.issue("apple", "a1", Identity("apple-sub-1", "x1y2@privaterelay.appleid.com", True, None))
    r = await _social(h, "apple", "a1", nonce="n-123", full_name="Ravi Kumar")
    assert r.status_code == 201, r.text
    uid = r.json()["user"]["id"]
    assert r.json()["user"]["full_name"] == "Ravi Kumar"
    assert idp.calls[-1] == {"provider": "apple", "id_token": "a1", "nonce": "n-123"}  # nonce passed through

    idp.issue("apple", "a2", Identity("apple-sub-1", None, False, None))  # Apple omits email later
    r = await _social(h, "apple", "a2", nonce="n-456")
    assert r.status_code == 200 and r.json()["user"]["id"] == uid, r.text
    assert r.json()["user"]["full_name"] == "Ravi Kumar"  # not overwritten with a blank name


async def test_first_sign_in_without_email_is_rejected(h: Harness, idp: FakeIdentityVerifier):
    idp.issue("apple", "a1", Identity("apple-sub-new", None, False, None))
    r = await _social(h, "apple", "a1", full_name="No Mail")
    assert r.status_code == 422 and r.json()["error"]["code"] == "email_required", r.text


async def test_links_to_existing_verified_password_account(h: Harness, idp: FakeIdentityVerifier):
    existing = await register(h, "linkme@test.parkezy.dev")
    idp.issue("google", "g1", Identity("g-link", "LinkMe@test.parkezy.dev", True, "Other Name"))
    r = await _social(h, "google", "g1")
    assert r.status_code == 200, r.text
    assert r.json()["user"]["id"] == existing["id"]
    assert r.json()["user"]["full_name"] == "Test User"  # existing profile is kept
    # The password still works for a verified account.
    r = await h.client.post("/v1/auth/login", json={"email": existing["email"], "password": "parking123"})
    assert r.status_code == 200


async def test_linking_an_unverified_account_locks_out_the_pre_registered_password(
    h: Harness, idp: FakeIdentityVerifier
):
    squatter = await register(h, "victim@test.parkezy.dev", verify=False)
    idp.issue("google", "g1", Identity("g-victim", "victim@test.parkezy.dev", True, "Real Owner"))
    r = await _social(h, "google", "g1")
    assert r.status_code == 200, r.text
    assert r.json()["user"]["id"] == squatter["id"] and r.json()["user"]["email_verified"] is True

    r = await h.client.post("/v1/auth/login", json={"email": "victim@test.parkezy.dev", "password": "parking123"})
    assert r.status_code == 401
    assert (await h.client.post("/v1/auth/refresh", json={"refresh_token": squatter["refresh"]})).status_code == 401
    assert (await h.client.get("/v1/me", headers=auth(squatter["token"]))).status_code == 401


async def test_unverified_provider_email_is_refused(h: Harness, idp: FakeIdentityVerifier):
    await register(h, "taken@test.parkezy.dev")
    idp.issue("google", "g1", Identity("g-unv", "taken@test.parkezy.dev", False, "Mallory"))
    r = await _social(h, "google", "g1")
    assert r.status_code == 403 and r.json()["error"]["code"] == "provider_email_unverified", r.text
    idp.issue("google", "g2", Identity("g-unv2", "fresh@test.parkezy.dev", False, "Fresh"))
    r = await _social(h, "google", "g2")
    assert r.status_code == 403 and r.json()["error"]["code"] == "provider_email_unverified"


async def test_same_email_different_providers_share_one_account(h: Harness, idp: FakeIdentityVerifier):
    idp.issue("google", "g1", Identity("g-1", "both@example.com"))
    idp.issue("apple", "a1", Identity("a-1", "both@example.com"))
    google = (await _social(h, "google", "g1")).json()["user"]
    r = await _social(h, "apple", "a1", full_name="Ignored")
    assert r.status_code == 200 and r.json()["user"]["id"] == google["id"], r.text


async def test_bad_requests(h: Harness, idp: FakeIdentityVerifier):
    idp.issue("google", "good", Identity("g-ok", "ok@example.com"))
    r = await _social(h, "google", "forged-token")
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_id_token", r.text
    r = await _social(h, "facebook", "good")
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_failed"
    r = await h.client.post("/v1/auth/social", json={"provider": "google"})
    assert r.status_code == 422
    r = await _social(h, "google", "")
    assert r.status_code == 422
    # A Google token is not accepted as an Apple token.
    r = await _social(h, "apple", "good")
    assert r.status_code == 401
    assert (await _social(h, "google", "good")).status_code == 201


async def test_password_less_account_rules(h: Harness, idp: FakeIdentityVerifier):
    idp.issue("google", "g1", Identity("g-np", "nopass@example.com"))
    data = (await _social(h, "google", "g1")).json()
    token = data["tokens"]["access_token"]

    r = await h.client.post("/v1/auth/login", json={"email": "nopass@example.com", "password": "anything123"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"
    r = await h.client.post(
        "/v1/auth/change-password",
        json={"current_password": "whatever1", "new_password": "parking456"},
        headers=auth(token),
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_password", r.text

    r = await h.client.request("DELETE", "/v1/me", json={}, headers=auth(token))
    assert r.status_code == 200, r.text

    # Deleted account: the same Google identity starts a brand-new account.
    r = await _social(h, "google", "g1")
    assert r.status_code == 201, r.text
    assert r.json()["user"]["id"] != data["user"]["id"]


async def test_suspended_account_cannot_sign_in(h: Harness, idp: FakeIdentityVerifier):
    from sqlalchemy import update

    from app.db.models import User

    idp.issue("google", "g1", Identity("g-sus", "sus@example.com"))
    uid = (await _social(h, "google", "g1")).json()["user"]["id"]
    async with h.container.session_factory() as s:
        await s.execute(update(User).where(User.id == uid).values(status="suspended"))
        await s.commit()
    r = await _social(h, "google", "g1")
    assert r.status_code == 401, r.text


async def test_concurrent_first_sign_ins_create_one_account(h: Harness, idp: FakeIdentityVerifier):
    import asyncio

    idp.issue("google", "g1", Identity("g-race", "race@example.com"))
    responses = await asyncio.gather(*[_social(h, "google", "g1") for _ in range(5)])
    assert all(r.status_code in (200, 201) for r in responses), [r.text for r in responses]
    assert len({r.json()["user"]["id"] for r in responses}) == 1
    assert sum(r.status_code == 201 for r in responses) == 1
