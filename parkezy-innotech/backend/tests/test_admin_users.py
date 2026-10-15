"""Admin user management.

Contract
--------
GET  /v1/admin/users?q=&status=&limit=&cursor=   -> Page[AdminUserOut], newest first
GET  /v1/admin/users/{user_id}                   -> AdminUserDetail (AdminUserOut + listings_count,
                                                    bookings_count, suspension_reason, suspended_at)
POST /v1/admin/users/{user_id}/suspend  body {reason: 3..500 chars} -> 200 AdminUserDetail
POST /v1/admin/users/{user_id}/unsuspend                            -> 200 AdminUserDetail

AdminUserOut = {id, email, full_name, phone, status, email_verified, is_host, is_commercial_host,
                is_admin, created_at}

Rules
-----
* Admin only (403 for everyone else, 401 without a token).
* `q` is a case-insensitive substring match on email or full name; `status` filters exactly.
* Suspending: revokes every refresh token, rejects the current access token, blocks login,
  hides the user's listings from search/detail. Unsuspending restores login and listings
  (sessions stay revoked - the user signs in again).
* 409 codes: `cannot_suspend_self`, `cannot_suspend_admin`, `already_suspended`, `not_suspended`,
  `user_deleted`.
"""

import uuid

from tests.conftest import Harness
from tests.helpers import BANGALORE, auth, book, create_listing, make_host, register

ADMIN = "admin@test.parkezy.dev"


async def _admin(h: Harness) -> dict:
    return await register(h, ADMIN)


async def _suspend(h: Harness, admin: dict, user_id: str, reason: str | None = "Fraudulent listings"):
    body = {} if reason is None else {"reason": reason}
    return await h.client.post(f"/v1/admin/users/{user_id}/suspend", json=body, headers=auth(admin["token"]))


async def test_list_search_and_filter(h: Harness):
    admin = await _admin(h)
    alice = await register(h, "alice.sharma@test.parkezy.dev")
    bob = await register(h, "bob@test.parkezy.dev")
    h.clock.advance(seconds=1)
    carol = await register(h, "carol@test.parkezy.dev")

    r = await h.client.get("/v1/admin/users", headers=auth(admin["token"]))
    assert r.status_code == 200, r.text
    ids = [u["id"] for u in r.json()["items"]]
    assert ids[0] == carol["id"] and set(ids) == {admin["id"], alice["id"], bob["id"], carol["id"]}
    row = next(u for u in r.json()["items"] if u["id"] == alice["id"])
    assert row["status"] == "active" and row["email_verified"] is True and "password_hash" not in row

    r = await h.client.get("/v1/admin/users", params={"q": "ALICE"}, headers=auth(admin["token"]))
    assert [u["id"] for u in r.json()["items"]] == [alice["id"]]
    r = await h.client.get("/v1/admin/users", params={"q": "sharma"}, headers=auth(admin["token"]))
    assert [u["id"] for u in r.json()["items"]] == [alice["id"]]
    r = await h.client.get("/v1/admin/users", params={"q": "nobody-matches"}, headers=auth(admin["token"]))
    assert r.json()["items"] == []
    # LIKE wildcards in the query are treated literally.
    r = await h.client.get("/v1/admin/users", params={"q": "%"}, headers=auth(admin["token"]))
    assert r.json()["items"] == []

    await _suspend(h, admin, bob["id"])
    r = await h.client.get("/v1/admin/users", params={"status": "suspended"}, headers=auth(admin["token"]))
    assert [u["id"] for u in r.json()["items"]] == [bob["id"]]
    r = await h.client.get("/v1/admin/users", params={"status": "bogus"}, headers=auth(admin["token"]))
    assert r.status_code == 422


async def test_pagination(h: Harness):
    admin = await _admin(h)
    users = [admin["id"]]
    for _ in range(4):
        h.clock.advance(seconds=1)
        users.append((await register(h))["id"])
    seen, cursor = [], None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = (await h.client.get("/v1/admin/users", params=params, headers=auth(admin["token"]))).json()
        seen += [u["id"] for u in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == list(reversed(users))
    r = await h.client.get("/v1/admin/users", params={"cursor": "zzz"}, headers=auth(admin["token"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_cursor"
    r = await h.client.get("/v1/admin/users", params={"limit": 0}, headers=auth(admin["token"]))
    assert r.status_code == 422


async def test_user_detail_counts(h: Harness):
    admin = await _admin(h)
    host = await make_host(h)
    listing = await create_listing(h, host)
    await create_listing(h, host, title="Second")
    driver = await register(h)
    await book(h, driver, listing)

    r = await h.client.get(f"/v1/admin/users/{host['id']}", headers=auth(admin["token"]))
    assert r.status_code == 200, r.text
    assert (r.json()["listings_count"], r.json()["bookings_count"]) == (2, 0)
    assert r.json()["is_host"] is True and r.json()["suspension_reason"] is None
    r = await h.client.get(f"/v1/admin/users/{driver['id']}", headers=auth(admin["token"]))
    assert (r.json()["listings_count"], r.json()["bookings_count"]) == (0, 1)

    assert (await h.client.get(f"/v1/admin/users/{uuid.uuid4()}", headers=auth(admin["token"]))).status_code == 404
    assert (await h.client.get("/v1/admin/users/not-a-uuid", headers=auth(admin["token"]))).status_code == 422


async def test_suspend_cuts_off_every_session_and_hides_listings(h: Harness):
    admin = await _admin(h)
    host = await make_host(h)
    listing = await create_listing(h, host)

    r = await _suspend(h, admin, host["id"], "Fake photos")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "suspended" and r.json()["suspension_reason"] == "Fake photos"
    assert r.json()["suspended_at"]

    assert (await h.client.get("/v1/me", headers=auth(host["token"]))).status_code == 401
    assert (await h.client.post("/v1/auth/refresh", json={"refresh_token": host["refresh"]})).status_code == 401
    r = await h.client.post("/v1/auth/login", json={"email": host["email"], "password": "parking123"})
    assert r.status_code == 401

    assert (await h.client.get(f"/v1/listings/{listing['id']}")).status_code == 404
    params = {"latitude": BANGALORE[0], "longitude": BANGALORE[1]}
    assert (await h.client.get("/v1/listings", params=params)).json() == []
    driver = await register(h)
    assert (await book(h, driver, listing)).status_code == 404

    r = await h.client.post(f"/v1/admin/users/{host['id']}/unsuspend", headers=auth(admin["token"]))
    assert r.status_code == 200 and r.json()["status"] == "active", r.text
    assert r.json()["suspension_reason"] is None
    # Old sessions stay dead; a fresh login works and the listing is back.
    assert (await h.client.post("/v1/auth/refresh", json={"refresh_token": host["refresh"]})).status_code == 401
    r = await h.client.post("/v1/auth/login", json={"email": host["email"], "password": "parking123"})
    assert r.status_code == 200
    assert (await h.client.get(f"/v1/listings/{listing['id']}")).status_code == 200
    assert (await book(h, driver, listing)).status_code == 201


async def test_suspension_guard_rails(h: Harness):
    admin = await _admin(h)
    user = await register(h)

    r = await _suspend(h, admin, admin["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "cannot_suspend_self", r.text

    for bad in (None, "", "  ", "x" * 501):
        r = await _suspend(h, admin, user["id"], bad)
        assert r.status_code == 422, (bad, r.text)

    assert (await _suspend(h, admin, user["id"])).status_code == 200
    r = await _suspend(h, admin, user["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_suspended"

    other = await register(h)
    r = await h.client.post(f"/v1/admin/users/{other['id']}/unsuspend", headers=auth(admin["token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_suspended"

    assert (await _suspend(h, admin, str(uuid.uuid4()))).status_code == 404


async def test_cannot_suspend_another_admin(h: Harness):
    from sqlalchemy import update

    from app.db.models import User

    admin = await _admin(h)
    second = await register(h)
    async with h.container.session_factory() as s:
        await s.execute(update(User).where(User.id == second["id"]).values(is_admin=True))
        await s.commit()
    r = await _suspend(h, admin, second["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "cannot_suspend_admin", r.text


async def test_deleted_users_cannot_be_suspended(h: Harness):
    admin = await _admin(h)
    user = await register(h)
    r = await h.client.request("DELETE", "/v1/me", json={"password": "parking123"}, headers=auth(user["token"]))
    assert r.status_code == 200, r.text
    r = await _suspend(h, admin, user["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "user_deleted", r.text


async def test_admin_only(h: Harness):
    user = await register(h)
    host = await make_host(h)
    for path in ("/v1/admin/users", f"/v1/admin/users/{user['id']}"):
        assert (await h.client.get(path, headers=auth(host["token"]))).status_code == 403
        assert (await h.client.get(path)).status_code == 401
    r = await h.client.post(
        f"/v1/admin/users/{user['id']}/suspend", json={"reason": "nope"}, headers=auth(host["token"])
    )
    assert r.status_code == 403
    r = await h.client.post(f"/v1/admin/users/{user['id']}/unsuspend", headers=auth(host["token"]))
    assert r.status_code == 403
    # The user is untouched.
    assert (await h.client.get("/v1/me", headers=auth(user["token"]))).status_code == 200
    admin = await _admin(h)
    assert (await h.client.get("/v1/admin/users", headers=auth(admin["token"]))).status_code == 200
