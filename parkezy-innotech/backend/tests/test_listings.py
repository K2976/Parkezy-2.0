import uuid

from tests.conftest import Harness
from tests.helpers import BANGALORE, auth, create_listing, make_host, register, upload_photo, window


async def test_only_verified_hosts_with_phone_can_host(h: Harness):
    unverified = await register(h, verify=False)
    r = await h.client.post("/v1/me/become-host", headers=auth(unverified["token"]))
    assert r.json()["error"]["code"] == "email_not_verified"
    no_phone = await register(h, phone=None)
    r = await h.client.post("/v1/me/become-host", headers=auth(no_phone["token"]))
    assert r.json()["error"]["code"] == "phone_required"
    driver = await register(h)
    r = await h.client.post("/v1/host/listings", json={}, headers=auth(driver["token"]))
    assert r.status_code == 403 and r.json()["error"]["code"] == "not_a_host"


async def test_create_listing_with_real_upload_and_public_detail(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    assert listing["status"] == "active"
    assert listing["currency"] == "INR" and listing["timezone"] == "Asia/Kolkata"
    assert [s["label"] for s in listing["slots"]] == ["A1", "A2"]
    assert [s["hourly_rate"] for s in listing["slots"]] == ["40.00", "60.00"]
    assert len(listing["media"]) == 1 and listing["media"][0]["url"].startswith("http")

    r = await h.client.get(f"/v1/listings/{listing['id']}")
    assert r.status_code == 200
    public = r.json()
    assert public["access_instructions"] is None
    assert public["host"]["first_name"] == "Test"


async def test_publish_requires_photos_and_upload_ownership(h: Harness):
    host = await make_host(h)
    other = await make_host(h)
    foreign_photo = await upload_photo(h, other["token"])
    body = {
        "title": "Spot",
        "address_line": "1 Road",
        "city": "Pune",
        "latitude": 18.5,
        "longitude": 73.8,
        "hourly_rate": "30",
        "slots": [{"label": "1"}],
    }
    r = await h.client.post("/v1/host/listings", json=body, headers=auth(host["token"]))
    assert r.json()["error"]["code"] == "photos_required"
    r = await h.client.post(
        "/v1/host/listings", json=body | {"photo_upload_ids": [foreign_photo]}, headers=auth(host["token"])
    )
    assert r.json()["error"]["code"] == "upload_invalid"
    r = await h.client.post("/v1/host/listings", json=body | {"publish": False}, headers=auth(host["token"]))
    assert r.status_code == 201 and r.json()["status"] == "draft"


async def test_upload_must_exist_and_type_is_checked(h: Harness):
    host = await make_host(h)
    r = await h.client.post(
        "/v1/uploads", json={"purpose": "listing_photo", "content_type": "application/pdf"}, headers=auth(host["token"])
    )
    assert r.json()["error"]["code"] == "content_type_not_allowed"
    r = await h.client.post(
        "/v1/uploads", json={"purpose": "listing_photo", "content_type": "image/png"}, headers=auth(host["token"])
    )
    r = await h.client.post(f"/v1/uploads/{r.json()['id']}/complete", headers=auth(host["token"]))
    assert r.json()["error"]["code"] == "upload_missing"


async def test_commercial_listing_needs_admin_grant(h: Harness):
    host = await make_host(h)
    admin = await register(h, "admin@test.parkezy.dev")
    photo = await upload_photo(h, host["token"])
    body = {
        "kind": "commercial",
        "title": "Mall P2",
        "address_line": "Forum Mall",
        "city": "Bengaluru",
        "latitude": 12.93,
        "longitude": 77.61,
        "hourly_rate": "50",
        "slots": [{"label": "P2-01", "floor": "P2"}],
        "photo_upload_ids": [photo],
    }
    r = await h.client.post("/v1/host/listings", json=body, headers=auth(host["token"]))
    assert r.json()["error"]["code"] == "not_commercial_host"
    r = await h.client.post(f"/v1/admin/users/{host['id']}/commercial-host", headers=auth(admin["token"]))
    assert r.status_code == 200 and r.json()["is_commercial_host"]
    r = await h.client.post("/v1/host/listings", json=body, headers=auth(host["token"]))
    assert r.status_code == 201 and r.json()["kind"] == "commercial"


async def test_update_listing_slots_and_ownership(h: Harness):
    host = await make_host(h)
    intruder = await make_host(h)
    listing = await create_listing(h, host)
    lid = listing["id"]
    r = await h.client.patch(
        f"/v1/host/listings/{lid}",
        json={
            "hourly_rate": "55.50",
            "is_24h": False,
            "open_time": "08:00",
            "close_time": "20:00",
            "access_instructions": "Gate code 4411",
        },
        headers=auth(host["token"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["hourly_rate"] == "55.50" and r.json()["open_time"] == "08:00:00"
    assert r.json()["access_instructions"] == "Gate code 4411"

    r = await h.client.patch(f"/v1/host/listings/{lid}", json={"hourly_rate": "1"}, headers=auth(intruder["token"]))
    assert r.status_code == 404

    r = await h.client.post(f"/v1/host/listings/{lid}/slots", json=[{"label": "A1"}], headers=auth(host["token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "duplicate"
    r = await h.client.post(f"/v1/host/listings/{lid}/slots", json=[{"label": "B1"}], headers=auth(host["token"]))
    assert len(r.json()["slots"]) == 3
    slot_id = r.json()["slots"][-1]["id"]
    r = await h.client.delete(f"/v1/host/listings/{lid}/slots/{slot_id}", headers=auth(host["token"]))
    assert len(r.json()["slots"]) == 2

    r = await h.client.patch(
        f"/v1/host/listings/{lid}",
        json={"is_24h": False, "open_time": "20:00", "close_time": "08:00"},
        headers=auth(host["token"]),
    )
    assert r.json()["error"]["code"] == "invalid_hours"


async def test_search_by_distance_filters_and_availability(h: Harness):
    host = await make_host(h)
    near = await create_listing(h, host, title="Near")
    await create_listing(
        h,
        host,
        title="Far cheap",
        latitude=BANGALORE[0] + 0.03,
        longitude=BANGALORE[1],
        hourly_rate="20",
        amenities=["covered"],
        slots=[{"label": "F1"}],
    )
    await create_listing(h, host, title="Other city", latitude=19.07, longitude=72.87)

    params = {"latitude": BANGALORE[0], "longitude": BANGALORE[1], "radius_km": 10}
    r = await h.client.get("/v1/listings", params=params)
    assert r.status_code == 200
    titles = [x["title"] for x in r.json()]
    assert titles == ["Near", "Far cheap"]
    assert r.json()[0]["distance_m"] < r.json()[1]["distance_m"]
    assert r.json()[0]["cover_photo_url"]

    r = await h.client.get("/v1/listings", params=params | {"sort": "price"})
    assert [x["title"] for x in r.json()] == ["Far cheap", "Near"]
    r = await h.client.get("/v1/listings", params=params | {"amenities": ["cctv"]})
    assert [x["title"] for x in r.json()] == ["Near"]
    r = await h.client.get("/v1/listings", params=params | {"slot_type": "ev"})
    assert [x["title"] for x in r.json()] == ["Near"]
    r = await h.client.get("/v1/listings", params=params | {"radius_km": 100})
    assert r.json()["error"]["code"] == "validation_failed"

    start, end = window(h)
    r = await h.client.get("/v1/listings", params=params | {"starts_at": start, "ends_at": end})
    by_title = {x["title"]: x for x in r.json()}
    assert by_title["Near"]["available_slots"] == 2

    driver = await register(h)
    r = await h.client.post(
        "/v1/bookings",
        json={"listing_id": near["id"], "starts_at": start, "ends_at": end},
        headers=auth(driver["token"]) | {"Idempotency-Key": uuid.uuid4().hex},
    )
    assert r.status_code == 201
    # Booking bumps the cache version, so search reflects it immediately.
    r = await h.client.get("/v1/listings", params=params | {"starts_at": start, "ends_at": end})
    assert {x["title"]: x for x in r.json()}["Near"]["available_slots"] == 1

    r = await h.client.get(f"/v1/listings/{near['id']}", params={"starts_at": start, "ends_at": end})
    assert sorted(s["available"] for s in r.json()["slots"]) == [False, True]


async def test_paused_listing_disappears_from_search(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    params = {"latitude": BANGALORE[0], "longitude": BANGALORE[1]}
    assert len((await h.client.get("/v1/listings", params=params)).json()) == 1
    await h.client.patch(f"/v1/host/listings/{listing['id']}", json={"status": "paused"}, headers=auth(host["token"]))
    assert (await h.client.get("/v1/listings", params=params)).json() == []
    assert (await h.client.get(f"/v1/listings/{listing['id']}")).status_code == 404


async def test_public_config_comes_from_platform_settings(h: Harness):
    r = await h.client.get("/v1/config")
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["gst_rate"] == "0.18" and cfg["currency"] == "INR" and cfg["payment_mode"] == "pay_at_venue"
    admin = await register(h, "admin@test.parkezy.dev")
    r = await h.client.patch("/v1/admin/settings", json={"changes": {"gst_rate": "0.12"}}, headers=auth(admin["token"]))
    assert r.status_code == 200
    assert (await h.client.get("/v1/config")).json()["gst_rate"] == "0.12"
    r = await h.client.patch("/v1/admin/settings", json={"changes": {"gst_rate": "5"}}, headers=auth(admin["token"]))
    assert r.status_code == 422
    r = await h.client.patch("/v1/admin/settings", json={"changes": {"nope": 1}}, headers=auth(admin["token"]))
    assert r.status_code == 404
