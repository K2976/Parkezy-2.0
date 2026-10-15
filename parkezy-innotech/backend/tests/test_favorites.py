"""Favourite / saved spots.

Contract
--------
PUT    /v1/me/favorites/{listing_id}   -> 204 (idempotent)
DELETE /v1/me/favorites/{listing_id}   -> 204 (idempotent; also 204 if it was never saved)
GET    /v1/me/favorites                -> Page[ListingSummary], most recently saved first

GET /v1/listings/{id} gains `is_favorite` (false for anonymous callers).

Rules
-----
* Only bookable listings can be saved: unknown, draft, paused or archived -> 404.
* Saved listings that are later paused/archived are hidden from the list (not deleted):
  they come back if the listing is reactivated.
* Per-user: one user's favourites are never visible to another.
* limit must be > 0 (422); larger than max_page_size is capped, like other list endpoints.
"""

import asyncio
import uuid

from tests.conftest import Harness
from tests.helpers import auth, create_listing, make_host, register


async def _save(h: Harness, user: dict, listing_id: str):
    return await h.client.put(f"/v1/me/favorites/{listing_id}", headers=auth(user["token"]))


async def _unsave(h: Harness, user: dict, listing_id: str):
    return await h.client.delete(f"/v1/me/favorites/{listing_id}", headers=auth(user["token"]))


async def _ids(h: Harness, user: dict, **params) -> list[str]:
    r = await h.client.get("/v1/me/favorites", params=params, headers=auth(user["token"]))
    assert r.status_code == 200, r.text
    return [x["id"] for x in r.json()["items"]]


async def test_save_list_and_remove(h: Harness):
    host = await make_host(h)
    a = await create_listing(h, host, title="Spot A")
    b = await create_listing(h, host, title="Spot B")
    driver = await register(h)

    assert (await _save(h, driver, a["id"])).status_code == 204
    h.clock.advance(seconds=1)
    assert (await _save(h, driver, b["id"])).status_code == 204
    assert await _ids(h, driver) == [b["id"], a["id"]]  # newest first

    page = (await h.client.get("/v1/me/favorites", headers=auth(driver["token"]))).json()
    item = page["items"][0]
    assert item["title"] == "Spot B" and item["hourly_rate"] == "40.00" and "cover_photo_url" in item

    assert (await _unsave(h, driver, a["id"])).status_code == 204
    assert await _ids(h, driver) == [b["id"]]


async def test_save_and_remove_are_idempotent(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    for _ in range(3):
        assert (await _save(h, driver, listing["id"])).status_code == 204
    assert await _ids(h, driver) == [listing["id"]]
    for _ in range(2):
        assert (await _unsave(h, driver, listing["id"])).status_code == 204
    assert await _ids(h, driver) == []
    never_saved = await create_listing(h, host, title="Never")
    assert (await _unsave(h, driver, never_saved["id"])).status_code == 204


async def test_concurrent_saves_store_one_row(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    responses = await asyncio.gather(*[_save(h, driver, listing["id"]) for _ in range(6)])
    assert [r.status_code for r in responses] == [204] * 6, [r.text for r in responses]
    assert await _ids(h, driver) == [listing["id"]]


async def test_only_bookable_listings_can_be_saved(h: Harness):
    host = await make_host(h)
    driver = await register(h)
    assert (await _save(h, driver, str(uuid.uuid4()))).status_code == 404
    assert (await h.client.put("/v1/me/favorites/not-a-uuid", headers=auth(driver["token"]))).status_code == 422

    paused = await create_listing(h, host, title="Paused")
    await h.client.patch(f"/v1/host/listings/{paused['id']}", json={"status": "paused"}, headers=auth(host["token"]))
    assert (await _save(h, driver, paused["id"])).status_code == 404

    body = {
        "title": "Draft",
        "address_line": "1 Road",
        "city": "Pune",
        "latitude": 18.5,
        "longitude": 73.8,
        "hourly_rate": "30",
        "slots": [{"label": "1"}],
        "publish": False,
    }
    draft = (await h.client.post("/v1/host/listings", json=body, headers=auth(host["token"]))).json()
    assert (await _save(h, driver, draft["id"])).status_code == 404

    live = await create_listing(h, host, title="Live")
    assert (await _save(h, driver, live["id"])).status_code == 204


async def test_paused_favourite_is_hidden_then_returns(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    await _save(h, driver, listing["id"])
    url = f"/v1/host/listings/{listing['id']}"
    await h.client.patch(url, json={"status": "paused"}, headers=auth(host["token"]))
    assert await _ids(h, driver) == []
    await h.client.patch(url, json={"status": "active"}, headers=auth(host["token"]))
    assert await _ids(h, driver) == [listing["id"]]


async def test_archived_favourite_disappears(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    keep = await create_listing(h, host, title="Keep")
    driver = await register(h)
    await _save(h, driver, listing["id"])
    await _save(h, driver, keep["id"])
    r = await h.client.delete(f"/v1/host/listings/{listing['id']}", headers=auth(host["token"]))
    assert r.status_code == 204, r.text
    assert await _ids(h, driver) == [keep["id"]]


async def test_favourites_are_per_user_and_need_auth(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    d1, d2 = await register(h), await register(h)
    await _save(h, d1, listing["id"])
    assert await _ids(h, d1) == [listing["id"]]
    assert await _ids(h, d2) == []
    assert (await _unsave(h, d2, listing["id"])).status_code == 204  # no effect on d1
    assert await _ids(h, d1) == [listing["id"]]

    assert (await h.client.get("/v1/me/favorites")).status_code == 401
    assert (await h.client.put(f"/v1/me/favorites/{listing['id']}")).status_code == 401
    assert (await h.client.delete(f"/v1/me/favorites/{listing['id']}")).status_code == 401


async def test_listing_detail_shows_is_favorite(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    d1, d2 = await register(h), await register(h)
    await _save(h, d1, listing["id"])
    url = f"/v1/listings/{listing['id']}"
    assert (await h.client.get(url, headers=auth(d1["token"]))).json()["is_favorite"] is True
    assert (await h.client.get(url, headers=auth(d2["token"]))).json()["is_favorite"] is False
    assert (await h.client.get(url)).json()["is_favorite"] is False
    await _unsave(h, d1, listing["id"])
    assert (await h.client.get(url, headers=auth(d1["token"]))).json()["is_favorite"] is False


async def test_pagination(h: Harness):
    host = await make_host(h)
    driver = await register(h)
    saved = []
    for i in range(5):
        listing = await create_listing(h, host, title=f"Spot L{i}")
        await _save(h, driver, listing["id"])
        saved.append(listing["id"])
        h.clock.advance(seconds=1)

    seen, cursor = [], None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = (await h.client.get("/v1/me/favorites", params=params, headers=auth(driver["token"]))).json()
        seen += [x["id"] for x in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == list(reversed(saved))

    r = await h.client.get("/v1/me/favorites", params={"limit": 0}, headers=auth(driver["token"]))
    assert r.status_code == 422, r.text
    # Like every other list endpoint, an oversized limit is capped at max_page_size, not rejected.
    assert await _ids(h, driver, limit=1000) == list(reversed(saved))
    r = await h.client.get("/v1/me/favorites", params={"cursor": "nope"}, headers=auth(driver["token"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_cursor"
