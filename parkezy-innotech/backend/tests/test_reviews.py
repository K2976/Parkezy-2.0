"""Reviews and ratings.

Contract
--------
POST   /v1/bookings/{booking_id}/review      driver of a *completed* booking -> 201 ReviewOut
       body {rating: int 1..5, comment?: str <= 1000 chars (blank -> null)}
PATCH  /v1/reviews/{review_id}               author only, inside the review window -> 200 ReviewOut
DELETE /v1/reviews/{review_id}               author only -> 204
POST   /v1/host/reviews/{review_id}/reply    host of the listing, once -> 200 ReviewOut (host_reply set)
GET    /v1/listings/{listing_id}/reviews     public, newest first, Page {items, next_cursor}

ReviewOut = {id, booking_id, listing_id, rating, comment, author: {first_name}, host_reply,
             host_replied_at, created_at, updated_at}

Rules
-----
* One review per booking (`already_reviewed`, 409).
* Only completed bookings (`not_reviewable`, 409): not confirmed, cancelled, expired (no-show).
* Window: `review_window_days` platform setting (seed 14) after check-out (`review_window_closed`, 409);
  applies to create and edit.
* Non-participants and the host get 404 on POST /review (the booking is not theirs to review).
* listings.rating_avg (2 dp) / rating_count are recomputed on create, edit and delete;
  rating_avg is null when there are no reviews. Visible on detail and search results.
"""

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
    parse,
    register,
    relogin,
    slot_id,
    window,
)


async def _completed(h: Harness, **listing_overrides):
    host = await make_host(h)
    listing = await create_listing(h, host, **listing_overrides)
    driver = await register(h)
    b = (await book(h, driver, listing, slot_id=slot_id(listing))).json()
    done = await complete_booking(h, host, driver, b)
    return host, listing, driver, done


async def _complete_together(h: Harness, host: dict, pairs: list[tuple[dict, dict]]) -> None:
    """Complete several bookings that share one window: check everyone in, then everyone out."""
    for driver, b in pairs:
        await check_in(h, host, driver, b)
    h.clock.advance(seconds=(parse(pairs[0][1]["ends_at"]) - h.clock.now()).total_seconds())
    await relogin(h, host)
    for driver, b in pairs:
        await relogin(h, driver)
        r = await h.client.post(f"/v1/bookings/{b['id']}/check-out", headers=auth(driver["token"]))
        assert r.status_code == 200 and r.json()["status"] == "completed", r.text


async def _review(h: Harness, user: dict, booking_id: str, **body):
    return await h.client.post(
        f"/v1/bookings/{booking_id}/review", json={"rating": 5} | body, headers=auth(user["token"])
    )


async def test_driver_reviews_completed_booking_and_listing_rating_updates(h: Harness):
    host, listing, driver, b = await _completed(h)
    r = await _review(h, driver, b["id"], rating=4, comment="  Easy to find, gate was open.  ")
    assert r.status_code == 201, r.text
    review = r.json()
    assert review["rating"] == 4 and review["comment"] == "Easy to find, gate was open."
    assert review["booking_id"] == b["id"] and review["listing_id"] == listing["id"]
    assert review["author"] == {"first_name": "Test"}  # never the full name or email
    assert review["host_reply"] is None

    detail = (await h.client.get(f"/v1/listings/{listing['id']}")).json()
    assert (detail["rating_avg"], detail["rating_count"]) == ("4.00", 1)
    params = {"latitude": BANGALORE[0], "longitude": BANGALORE[1]}
    found = next(x for x in (await h.client.get("/v1/listings", params=params)).json() if x["id"] == listing["id"])
    assert found["rating_avg"] == "4.00"

    r = await h.client.get(f"/v1/listings/{listing['id']}/reviews")  # public: no auth needed
    assert r.status_code == 200, r.text
    assert [x["id"] for x in r.json()["items"]] == [review["id"]]
    assert r.json()["next_cursor"] is None


async def test_average_is_recomputed_across_reviews_edits_and_deletes(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    d1, d2 = await register(h), await register(h)
    b1 = (await book(h, d1, listing, slot_id=slot_id(listing, "A1"))).json()
    b2 = (await book(h, d2, listing, slot_id=slot_id(listing, "A2"))).json()
    await _complete_together(h, host, [(d1, b1), (d2, b2)])

    r1 = (await _review(h, d1, b1["id"], rating=5)).json()
    await _review(h, d2, b2["id"], rating=4)
    detail = (await h.client.get(f"/v1/listings/{listing['id']}")).json()
    assert (detail["rating_avg"], detail["rating_count"]) == ("4.50", 2)

    r = await h.client.patch(f"/v1/reviews/{r1['id']}", json={"rating": 1}, headers=auth(d1["token"]))
    assert r.status_code == 200 and r.json()["rating"] == 1, r.text
    assert (await h.client.get(f"/v1/listings/{listing['id']}")).json()["rating_avg"] == "2.50"

    # Someone else cannot edit or delete it.
    r = await h.client.patch(f"/v1/reviews/{r1['id']}", json={"rating": 5}, headers=auth(d2["token"]))
    assert r.status_code == 404
    r = await h.client.delete(f"/v1/reviews/{r1['id']}", headers=auth(host["token"]))
    assert r.status_code == 404

    r = await h.client.delete(f"/v1/reviews/{r1['id']}", headers=auth(d1["token"]))
    assert r.status_code == 204, r.text
    detail = (await h.client.get(f"/v1/listings/{listing['id']}")).json()
    assert (detail["rating_avg"], detail["rating_count"]) == ("4.00", 1)
    assert (await h.client.delete(f"/v1/reviews/{r1['id']}", headers=auth(d1["token"]))).status_code == 404


async def test_rating_returns_to_null_when_last_review_is_deleted(h: Harness):
    _, listing, driver, b = await _completed(h)
    review = (await _review(h, driver, b["id"], rating=3)).json()
    assert (await h.client.delete(f"/v1/reviews/{review['id']}", headers=auth(driver["token"]))).status_code == 204
    detail = (await h.client.get(f"/v1/listings/{listing['id']}")).json()
    assert (detail["rating_avg"], detail["rating_count"]) == (None, 0)
    # After deleting, the driver may review again (the booking is still completed and in the window).
    assert (await _review(h, driver, b["id"], rating=2)).status_code == 201


async def test_only_one_review_per_booking(h: Harness):
    _, listing, driver, b = await _completed(h)
    assert (await _review(h, driver, b["id"])).status_code == 201
    r = await _review(h, driver, b["id"], rating=1)
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_reviewed", r.text
    assert (await h.client.get(f"/v1/listings/{listing['id']}")).json()["rating_count"] == 1


async def test_rating_and_comment_validation(h: Harness):
    _, _, driver, b = await _completed(h)
    for bad in (0, 6, -1, 4.5, None):
        r = await _review(h, driver, b["id"], rating=bad)
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_failed", (bad, r.text)
    r = await h.client.post(f"/v1/bookings/{b['id']}/review", json={}, headers=auth(driver["token"]))
    assert r.status_code == 422
    r = await _review(h, driver, b["id"], comment="x" * 1001)
    assert r.status_code == 422
    r = await _review(h, driver, b["id"], comment="   ")
    assert r.status_code == 201 and r.json()["comment"] is None, r.text


async def test_only_completed_bookings_can_be_reviewed(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)

    upcoming = (await book(h, driver, listing)).json()
    r = await _review(h, driver, upcoming["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_reviewable", r.text

    start, end = window(h, start_in_hours=6)
    cancelled = (await book(h, driver, listing, start=start, end=end)).json()
    await h.client.post(f"/v1/bookings/{cancelled['id']}/cancel", json={}, headers=auth(driver["token"]))
    r = await _review(h, driver, cancelled["id"])
    assert r.json()["error"]["code"] == "not_reviewable"

    # A completed booking still works for the same driver (proves the endpoint exists).
    done = (await book(h, driver, listing, start=window(h, 10)[0], end=window(h, 10)[1])).json()
    await complete_booking(h, host, driver, done)
    assert (await _review(h, driver, done["id"])).status_code == 201


async def test_no_show_cannot_be_reviewed(h: Harness):
    from app.workers.jobs import maintenance

    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    start, end = window(h, start_in_hours=1, hours=1)
    b = (await book(h, driver, listing, start=start, end=end)).json()
    h.clock.advance(hours=3)
    await maintenance(h.container)
    await relogin(h, driver)
    assert (await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))).json()["status"] == "expired"
    r = await _review(h, driver, b["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_reviewable", r.text


async def test_host_and_strangers_cannot_review_the_booking(h: Harness):
    host, _, driver, b = await _completed(h)
    stranger = await register(h)
    assert (await _review(h, host, b["id"])).status_code == 404
    assert (await _review(h, stranger, b["id"])).status_code == 404
    r = await h.client.post(f"/v1/bookings/{uuid.uuid4()}/review", json={"rating": 5}, headers=auth(driver["token"]))
    assert r.status_code == 404
    r = await h.client.post(f"/v1/bookings/{b['id']}/review", json={"rating": 5})
    assert r.status_code == 401
    assert (await _review(h, driver, b["id"])).status_code == 201


async def test_review_window_closes(h: Harness):
    _, _, driver, b = await _completed(h)
    first = await _completed(h)  # a second, independent completed booking for the edit check
    h.clock.advance(days=14, minutes=-1)
    await relogin(h, driver, first[2])
    review = await _review(h, first[2], first[3]["id"], rating=4)
    assert review.status_code == 201, review.text  # still inside 14 days

    h.clock.advance(days=1)
    await relogin(h, driver, first[2])
    r = await _review(h, driver, b["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "review_window_closed", r.text
    r = await h.client.patch(f"/v1/reviews/{review.json()['id']}", json={"rating": 1}, headers=auth(first[2]["token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "review_window_closed", r.text


async def test_host_can_reply_once_and_only_to_own_listing(h: Harness):
    host, listing, driver, b = await _completed(h)
    review = (await _review(h, driver, b["id"], rating=2, comment="Tight turn")).json()
    url = f"/v1/host/reviews/{review['id']}/reply"

    other_host = await make_host(h)
    assert (await h.client.post(url, json={"reply": "hi"}, headers=auth(other_host["token"]))).status_code == 404
    r = await h.client.post(url, json={"reply": "hi"}, headers=auth(driver["token"]))
    assert r.status_code == 403  # a plain driver is not a host
    r = await h.client.post(url, json={"reply": "   "}, headers=auth(host["token"]))
    assert r.status_code == 422

    r = await h.client.post(url, json={"reply": "Sorry! We widened the gate."}, headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    assert r.json()["host_reply"] == "Sorry! We widened the gate." and r.json()["host_replied_at"]
    r = await h.client.post(url, json={"reply": "Again"}, headers=auth(host["token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_replied"

    public = (await h.client.get(f"/v1/listings/{listing['id']}/reviews")).json()["items"][0]
    assert public["host_reply"] == "Sorry! We widened the gate."


async def test_listing_reviews_pagination_and_unknown_listing(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host, slots=[{"label": f"S{i}"} for i in range(5)])
    drivers = [await register(h) for _ in range(5)]
    bookings = [(await book(h, d, listing, slot_id=slot_id(listing, f"S{i}"))).json() for i, d in enumerate(drivers)]
    ids = []
    await _complete_together(h, host, list(zip(drivers, bookings, strict=True)))
    for d, b in zip(drivers, bookings, strict=True):
        h.clock.advance(seconds=1)
        ids.append((await _review(h, d, b["id"], rating=3)).json()["id"])

    seen, cursor = [], None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = (await h.client.get(f"/v1/listings/{listing['id']}/reviews", params=params)).json()
        seen += [x["id"] for x in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == list(reversed(ids))  # newest first, no duplicates, nothing skipped

    r = await h.client.get(f"/v1/listings/{listing['id']}/reviews", params={"limit": 0})
    assert r.status_code == 422
    r = await h.client.get(f"/v1/listings/{listing['id']}/reviews", params={"cursor": "garbage"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_cursor"
    assert (await h.client.get(f"/v1/listings/{uuid.uuid4()}/reviews")).status_code == 404


async def test_reviews_of_paused_listing_are_hidden(h: Harness):
    host, listing, driver, b = await _completed(h)
    assert (await _review(h, driver, b["id"])).status_code == 201
    assert len((await h.client.get(f"/v1/listings/{listing['id']}/reviews")).json()["items"]) == 1
    r = await h.client.patch(
        f"/v1/host/listings/{listing['id']}", json={"status": "paused"}, headers=auth(host["token"])
    )
    assert r.status_code == 200, r.text
    assert (await h.client.get(f"/v1/listings/{listing['id']}/reviews")).status_code == 404


async def test_concurrent_duplicate_reviews_store_only_one(h: Harness):
    import asyncio

    _, listing, driver, b = await _completed(h)
    responses = await asyncio.gather(*[_review(h, driver, b["id"], rating=5) for _ in range(5)])
    codes = sorted(r.status_code for r in responses)
    assert codes == [201, 409, 409, 409, 409], codes
    assert (await h.client.get(f"/v1/listings/{listing['id']}")).json()["rating_count"] == 1


async def test_review_survives_listing_rate_change_and_time(h: Harness):
    """Regression guard: the rating is per listing, not per booking price or slot."""
    host, listing, driver, b = await _completed(h)
    await _review(h, driver, b["id"], rating=5)
    await h.client.patch(f"/v1/host/listings/{listing['id']}", json={"hourly_rate": "99"}, headers=auth(host["token"]))
    h.clock.advance(days=60)  # ratings do not decay, and the listing stays rated after the review window
    detail = (await h.client.get(f"/v1/listings/{listing['id']}")).json()
    assert (detail["rating_avg"], detail["rating_count"]) == ("5.00", 1)
