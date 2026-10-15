"""Delete (archive) a listing.

Contract
--------
DELETE /v1/host/listings/{listing_id}  -> 204, soft delete: status becomes `archived`.

Rules
-----
* Owner only: other hosts get 404, non-hosts 403 `not_a_host`, no token 401.
* Refused while the listing has any live booking (pending_approval, pending_payment, confirmed,
  checked_in) -> 409 `listing_has_active_bookings`, details {"active_bookings": n}.
  The same rule applies to PATCH {"status": "archived"}.
* After deletion the listing is gone everywhere: public detail/search 404/absent, host list and
  host detail, PATCH, DELETE again -> 404; quote/booking -> 404.
* History survives: drivers can still open their past bookings for that listing.
* Drafts can be deleted.
"""

import asyncio
import uuid

from tests.conftest import Harness
from tests.helpers import (
    BANGALORE,
    auth,
    book,
    check_in,
    complete_booking,
    create_listing,
    make_host,
    register,
    slot_id,
    window,
)


async def _delete(h: Harness, user: dict, listing_id: str):
    return await h.client.delete(f"/v1/host/listings/{listing_id}", headers=auth(user["token"]))


async def test_delete_hides_listing_everywhere(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    keep = await create_listing(h, host, title="Keep me")
    lid = listing["id"]

    r = await _delete(h, host, lid)
    assert r.status_code == 204, r.text

    assert (await h.client.get(f"/v1/listings/{lid}")).status_code == 404
    params = {"latitude": BANGALORE[0], "longitude": BANGALORE[1]}
    assert [x["id"] for x in (await h.client.get("/v1/listings", params=params)).json()] == [keep["id"]]
    mine = (await h.client.get("/v1/host/listings", headers=auth(host["token"]))).json()
    ids = [x["id"] for x in (mine["items"] if isinstance(mine, dict) else mine)]
    assert ids == [keep["id"]]
    assert (await h.client.get(f"/v1/host/listings/{lid}", headers=auth(host["token"]))).status_code == 404
    r = await h.client.patch(f"/v1/host/listings/{lid}", json={"hourly_rate": "10"}, headers=auth(host["token"]))
    assert r.status_code == 404
    assert (await _delete(h, host, lid)).status_code == 404

    driver = await register(h)
    start, end = window(h)
    r = await h.client.post("/v1/bookings/quote", json={"listing_id": lid, "starts_at": start, "ends_at": end})
    assert r.status_code == 404
    assert (await book(h, driver, listing)).status_code == 404


async def test_cannot_delete_with_live_bookings(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing)).json()

    r = await _delete(h, host, listing["id"])
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "listing_has_active_bookings"
    assert r.json()["error"]["details"]["active_bookings"] == 1
    r = await h.client.patch(
        f"/v1/host/listings/{listing['id']}", json={"status": "archived"}, headers=auth(host["token"])
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "listing_has_active_bookings", r.text
    assert (await h.client.get(f"/v1/listings/{listing['id']}")).status_code == 200  # still live

    await h.client.post(f"/v1/bookings/{b['id']}/cancel", json={}, headers=auth(driver["token"]))
    assert (await _delete(h, host, listing["id"])).status_code == 204


async def test_pending_request_and_checked_in_bookings_block_deletion(h: Harness):
    host = await make_host(h)
    manual = await create_listing(h, host, auto_accept=False)
    driver = await register(h)
    pending = (await book(h, driver, manual)).json()
    assert pending["status"] == "pending_approval"
    r = await _delete(h, host, manual["id"])
    assert r.json()["error"]["code"] == "listing_has_active_bookings"

    instant = await create_listing(h, host, title="Instant")
    b = (await book(h, driver, instant, slot_id=slot_id(instant))).json()
    await check_in(h, host, driver, b)
    r = await _delete(h, host, instant["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "listing_has_active_bookings", r.text


async def test_past_bookings_stay_visible_after_deletion(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing, slot_id=slot_id(listing))).json()
    await complete_booking(h, host, driver, b)

    assert (await _delete(h, host, listing["id"])).status_code == 204
    r = await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))
    assert r.status_code == 200, r.text
    assert r.json()["listing"]["title"] == listing["title"]
    past = (await h.client.get("/v1/bookings", params={"group": "past"}, headers=auth(driver["token"]))).json()
    assert b["id"] in [x["id"] for x in past["items"]]
    r = await h.client.get("/v1/host/bookings", params={"group": "past"}, headers=auth(host["token"]))
    assert b["id"] in [x["id"] for x in r.json()["items"]]


async def test_only_the_owner_can_delete(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    other_host = await make_host(h)
    driver = await register(h)
    assert (await _delete(h, other_host, listing["id"])).status_code == 404
    r = await _delete(h, driver, listing["id"])
    assert r.status_code == 403 and r.json()["error"]["code"] == "not_a_host"
    assert (await h.client.delete(f"/v1/host/listings/{listing['id']}")).status_code == 401
    assert (await _delete(h, host, str(uuid.uuid4()))).status_code == 404
    assert (await h.client.delete("/v1/host/listings/not-a-uuid", headers=auth(host["token"]))).status_code == 422
    assert (await h.client.get(f"/v1/listings/{listing['id']}")).status_code == 200
    assert (await _delete(h, host, listing["id"])).status_code == 204


async def test_draft_can_be_deleted(h: Harness):
    host = await make_host(h)
    body = {
        "title": "Draft spot",
        "address_line": "1 Road",
        "city": "Pune",
        "latitude": 18.5,
        "longitude": 73.8,
        "hourly_rate": "30",
        "slots": [{"label": "1"}],
        "publish": False,
    }
    draft = (await h.client.post("/v1/host/listings", json=body, headers=auth(host["token"]))).json()
    assert draft["status"] == "draft"
    assert (await _delete(h, host, draft["id"])).status_code == 204
    assert (await h.client.get(f"/v1/host/listings/{draft['id']}", headers=auth(host["token"]))).status_code == 404


async def test_delete_racing_a_booking_never_leaves_an_orphan(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    deleted, booked = await asyncio.gather(_delete(h, host, listing["id"]), book(h, driver, listing))
    # Either the delete wins (booking refused) or the booking wins (delete refused) - never both.
    assert (deleted.status_code, booked.status_code) in ((204, 404), (204, 409), (409, 201)), (
        deleted.text,
        booked.text,
    )
    if booked.status_code == 201:
        assert (await h.client.get(f"/v1/listings/{listing['id']}")).status_code == 200
