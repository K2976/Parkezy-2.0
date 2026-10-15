"""Notification preferences - edge cases for the endpoints the settings screen will use.

GET/PUT /v1/me/notification-preferences already exist; these tests pin their behaviour before the
mobile screen is built on top of them.

Shape: {"push": {category: bool}, "email": {category: bool}} with categories
bookings, reminders, receipts, disputes. Anything never set is enabled. PUT is a partial update.
The in-app inbox (GET /v1/notifications) is never muted.
"""

from tests.conftest import Harness
from tests.helpers import auth, book, create_listing, make_host, register

CATEGORIES = {"bookings", "reminders", "receipts", "disputes"}
URL = "/v1/me/notification-preferences"


async def test_defaults_are_all_enabled(h: Harness):
    user = await register(h)
    r = await h.client.get(URL, headers=auth(user["token"]))
    assert r.status_code == 200, r.text
    prefs = r.json()
    assert set(prefs) == {"push", "email"}
    for channel in ("push", "email"):
        assert prefs[channel] == {c: True for c in CATEGORIES}


async def test_partial_update_keeps_everything_else(h: Harness):
    user = await register(h)
    r = await h.client.put(URL, json={"push": {"reminders": False}}, headers=auth(user["token"]))
    assert r.status_code == 200, r.text
    r = await h.client.put(URL, json={"email": {"disputes": False}}, headers=auth(user["token"]))
    prefs = r.json()
    assert prefs["push"] == {c: c != "reminders" for c in CATEGORIES}
    assert prefs["email"] == {c: c != "disputes" for c in CATEGORIES}
    # Turning one back on.
    r = await h.client.put(URL, json={"push": {"reminders": True}}, headers=auth(user["token"]))
    assert r.json()["push"]["reminders"] is True and r.json()["email"]["disputes"] is False
    # An empty body changes nothing.
    r = await h.client.put(URL, json={}, headers=auth(user["token"]))
    assert r.status_code == 200 and r.json() == (await h.client.get(URL, headers=auth(user["token"]))).json()


async def test_unknown_category_or_bad_value_is_rejected(h: Harness):
    user = await register(h)
    for body in ({"push": {"marketing": False}}, {"email": {"receipts": "maybe"}}, {"push": ["bookings"]}):
        r = await h.client.put(URL, json=body, headers=auth(user["token"]))
        assert r.status_code == 422, (body, r.text)
    assert (await h.client.get(URL, headers=auth(user["token"]))).json()["push"] == {c: True for c in CATEGORIES}


async def test_preferences_are_per_user_and_need_auth(h: Harness):
    a, b = await register(h), await register(h)
    await h.client.put(URL, json={"email": {"receipts": False}}, headers=auth(a["token"]))
    assert (await h.client.get(URL, headers=auth(b["token"]))).json()["email"]["receipts"] is True
    assert (await h.client.get(URL)).status_code == 401
    assert (await h.client.put(URL, json={})).status_code == 401


async def test_muting_push_bookings_stops_push_but_not_email_or_inbox(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    token = {"token": "ExponentPushToken[muted-driver]", "platform": "android"}
    await h.client.post("/v1/me/push-tokens", json=token, headers=auth(driver["token"]))
    await h.client.put(URL, json={"push": {"bookings": False}}, headers=auth(driver["token"]))

    assert (await book(h, driver, listing)).status_code == 201
    await h.drain()
    assert not any(token["token"] in m.tokens for m in h.push.sent)
    assert any(e.to == driver["email"] and "Booking confirmed" in e.subject for e in h.email.sent)
    inbox = (await h.client.get("/v1/notifications", headers=auth(driver["token"]))).json()
    items = inbox["items"] if isinstance(inbox, dict) else inbox
    assert items, "the in-app inbox is never muted"


async def test_muting_email_bookings_stops_the_confirmation_email(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    await h.client.put(URL, json={"email": {"bookings": False}}, headers=auth(driver["token"]))
    assert (await book(h, driver, listing)).status_code == 201
    await h.drain()
    assert not any(e.to == driver["email"] and "Booking confirmed" in e.subject for e in h.email.sent)
