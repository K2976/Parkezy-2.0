"""Host dashboard numbers: every tile must match what the host can actually act on."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import Harness
from tests.helpers import auth, book, check_in, complete_booking, create_listing, make_host, register, slot_id, window


async def _dashboard(h: Harness, host: dict, days: int = 14) -> dict:
    r = await h.client.get("/v1/host/dashboard", params={"days": days}, headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    return r.json()


async def test_tiles_count_what_the_host_can_act_on(h: Harness):
    host = await make_host(h)
    instant = await create_listing(h, host, slots=[{"label": f"S{i}"} for i in range(4)])
    manual = await create_listing(h, host, title="Needs approval", auto_accept=False)
    paused = await create_listing(h, host, title="Paused spot")
    await h.client.patch(f"/v1/host/listings/{paused['id']}", json={"status": "paused"}, headers=auth(host["token"]))
    drivers = [await register(h) for _ in range(4)]

    parked = (await book(h, drivers[0], instant, slot_id=slot_id(instant, "S0"))).json()
    upcoming = (
        await book(h, drivers[1], instant, slot_id=slot_id(instant, "S1"), start=window(h, 30)[0], end=window(h, 30)[1])
    ).json()
    request = (await book(h, drivers[2], manual)).json()
    assert (parked["status"], upcoming["status"], request["status"]) == ("confirmed", "confirmed", "pending_approval")
    await check_in(h, host, drivers[0], parked)

    d = await _dashboard(h, host)
    assert d["active_listings"] == 2  # paused spots are not live
    assert (d["parked_now"], d["upcoming_bookings"], d["pending_requests"]) == (1, 1, 1)
    assert d["timezone"] == "Asia/Kolkata"


async def test_confirmed_booking_whose_time_passed_is_not_upcoming(h: Harness):
    """A no-show the maintenance job hasn't expired yet must not inflate 'Upcoming'."""
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    start, end = window(h, start_in_hours=1, hours=1)
    b = (await book(h, driver, listing, start=start, end=end)).json()
    assert (await _dashboard(h, host))["upcoming_bookings"] == 1

    h.clock.advance(hours=3)  # the window is over; no maintenance run, so it is still "confirmed"
    from tests.helpers import relogin

    await relogin(h, host, driver)
    r = await h.client.get(f"/v1/bookings/{b['id']}", headers=auth(driver["token"]))
    assert r.json()["status"] == "confirmed"
    assert (await _dashboard(h, host))["upcoming_bookings"] == 0


async def test_earnings_land_on_the_local_calendar_day(h: Harness):
    """Checked out at 19:00 UTC = 00:30 IST the next day: the chart bar is the IST date."""
    today = datetime.now(UTC).date()
    h.clock.current = datetime(today.year, today.month, today.day, 15, 10, tzinfo=UTC)
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing, slot_id=slot_id(listing))).json()  # 17:00-19:00 UTC
    done = await complete_booking(h, host, driver, b)
    checked_out = datetime.fromisoformat(done["checked_out_at"])
    utc_day = checked_out.astimezone(UTC).date()
    ist_day = checked_out.astimezone(ZoneInfo("Asia/Kolkata")).date()
    assert ist_day == utc_day + timedelta(days=1)  # the case that used to land on the wrong bar

    d = await _dashboard(h, host)
    assert d["daily_earnings"] == [{"day": ist_day.isoformat(), "amount": "68.00"}]
    assert d["earnings_period"] == d["earnings_total"] == "68.00"


async def test_pending_requests_are_found_behind_many_confirmed_bookings(h: Harness):
    """The dashboard asks for pending requests directly instead of filtering the first page of
    upcoming bookings, which could hide them behind 20+ confirmed ones."""
    host = await make_host(h)
    manual = await create_listing(h, host, title="Needs approval", auto_accept=False)
    instant = await create_listing(h, host, slots=[{"label": f"S{i}"} for i in range(25)])
    first = await register(h)
    request = (await book(h, first, manual)).json()
    drivers = [await register(h) for _ in range(25)]
    for i, d in enumerate(drivers):  # newer than the request, so they come first in the list
        assert (await book(h, d, instant, slot_id=slot_id(instant, f"S{i}"))).status_code == 201

    page = await h.client.get("/v1/host/bookings", params={"group": "upcoming"}, headers=auth(host["token"]))
    assert request["id"] not in [b["id"] for b in page.json()["items"]]  # the old approach missed it

    r = await h.client.get("/v1/host/bookings", params={"status": "pending_approval"}, headers=auth(host["token"]))
    assert r.status_code == 200, r.text
    assert [b["id"] for b in r.json()["items"]] == [request["id"]]
    assert (await _dashboard(h, host))["pending_requests"] == 1

    r = await h.client.get("/v1/host/bookings", params={"status": "bogus"}, headers=auth(host["token"]))
    assert r.status_code == 422


async def test_withdrawals_do_not_reduce_dashboard_earnings(hp: Harness):
    """Lifetime and period earnings stay what the host earned; payouts move money, they don't un-earn it."""
    from tests.test_payouts import UPI, _paid_completed_booking, _request

    host = await make_host(hp)
    listing = await create_listing(hp, host)
    await _paid_completed_booking(hp, host, listing)
    await hp.client.put("/v1/host/payout-account", json=UPI, headers=auth(host["token"]))
    assert (await _request(hp, host, "300.00")).status_code == 201
    d = await _dashboard(hp, host)
    assert d["earnings_total"] == d["earnings_period"] == "340.00"
    assert sum(float(x["amount"]) for x in d["daily_earnings"]) == 340.0
