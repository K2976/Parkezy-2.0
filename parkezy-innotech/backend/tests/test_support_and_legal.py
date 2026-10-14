"""Contact support (signed in and signed out) and the Terms / Privacy documents."""

from sqlalchemy import select

from app.db.models import SupportTicket
from tests.conftest import Harness
from tests.helpers import auth, book, create_listing, make_host, register

TICKET = {"category": "booking", "subject": "Gate was locked", "message": "The gate was locked when I arrived."}


async def test_signed_in_support_ticket_emails_team_and_user(h: Harness):
    host = await make_host(h)
    listing = await create_listing(h, host)
    driver = await register(h)
    b = (await book(h, driver, listing)).json()
    # A typed email is ignored for signed-in users: replies go to the verified account address.
    body = TICKET | {"booking_id": b["id"], "email": "someone-else@test.parkezy.dev"}
    r = await h.client.post("/v1/support", json=body, headers=auth(driver["token"]))
    assert r.status_code == 201, r.text
    ticket = r.json()
    assert ticket["status"] == "open" and len(ticket["reference"]) == 8

    h.email.sent.clear()
    await h.drain()
    team = [e for e in h.email.sent if e.to == h.container.settings.support_email]
    ack = [e for e in h.email.sent if e.to == driver["email"] and e.tags["template"] == "support_received"]
    assert len(team) == 1 and ticket["reference"] in team[0].subject
    assert "The gate was locked when I arrived." in team[0].text and b["id"] in team[0].text
    assert len(ack) == 1 and ticket["reference"] in ack[0].subject
    assert not any(e.to == "someone-else@test.parkezy.dev" for e in h.email.sent)
    await h.drain()  # at-least-once delivery never sends twice
    assert len([e for e in h.email.sent if e.to == h.container.settings.support_email]) == 1

    mine = (await h.client.get("/v1/support/tickets", headers=auth(driver["token"]))).json()
    assert [t["id"] for t in mine] == [ticket["id"]]
    assert (await h.client.get("/v1/support/tickets", headers=auth(host["token"]))).json() == []


async def test_signed_out_support_needs_an_email_and_cannot_attach_bookings(h: Harness):
    r = await h.client.post("/v1/support", json=TICKET | {"category": "account"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "email_required"
    body = TICKET | {"category": "account", "email": "locked-out@test.parkezy.dev", "name": "Locked Out"}
    r = await h.client.post("/v1/support", json=body)
    assert r.status_code == 201, r.text
    await h.drain()
    assert any(e.to == "locked-out@test.parkezy.dev" for e in h.email.sent)
    async with h.container.session_factory() as s:
        saved = (await s.execute(select(SupportTicket))).scalar_one()
        assert saved.user_id is None and saved.name == "Locked Out"

    # Someone else's booking id is refused, signed in or not, without revealing it exists.
    host = await make_host(h)
    listing = await create_listing(h, host)
    b = (await book(h, await register(h), listing)).json()
    stranger = await register(h)
    r = await h.client.post("/v1/support", json=body | {"booking_id": b["id"]}, headers=auth(stranger["token"]))
    assert r.status_code == 404
    assert (await h.client.post("/v1/support", json=body | {"booking_id": b["id"]})).status_code == 404
    bad = await h.client.post("/v1/support", json=body, headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401


async def test_legal_documents_reflect_live_rules(h: Harness):
    for doc, title in (("terms", "Terms of Service"), ("privacy", "Privacy Policy")):
        r = await h.client.get(f"/v1/legal/{doc}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["title"] == title and data["sections"] and data["version"]
        page = await h.client.get(f"/legal/{doc}")
        assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
        assert title in page.text and h.container.settings.support_email in page.text
    assert (await h.client.get("/v1/legal/cookies")).status_code == 422

    def text(doc: dict) -> str:
        return " ".join(b.get("text") or " ".join(b.get("items") or []) for s in doc["sections"] for b in s["blocks"])

    before = text((await h.client.get("/v1/legal/terms")).json())
    assert "cancel at least 60 minutes" in before
    admin = await register(h, "admin@test.parkezy.dev")
    r = await h.client.patch(
        "/v1/admin/settings", json={"changes": {"free_cancellation_minutes": 120}}, headers=auth(admin["token"])
    )
    assert r.status_code == 200, r.text
    assert "cancel at least 120 minutes" in text((await h.client.get("/v1/legal/terms")).json())
