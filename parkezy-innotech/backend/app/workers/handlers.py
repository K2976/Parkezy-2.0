"""Outbox event handlers. Adding a new event = add one decorated function (open/closed).

Each handler must be idempotent: the outbox guarantees at-least-once delivery.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import Booking, Dispute, SupportTicket, User
from app.services.booking_service import BookingService, BookingView
from app.services.email_service import EmailService
from app.services.notification_service import EmailSpec, NotificationService
from app.services.outbox import Event
from app.services.payment_service import PaymentService


@dataclass
class HandlerContext:
    session: AsyncSession
    settings: Settings
    notifications: NotificationService
    email: EmailService
    bookings: BookingService
    payments: PaymentService


Handler = Callable[[HandlerContext, str, dict], Awaitable[None]]
HANDLERS: dict[str, Handler] = {}


def handles(*events: Event):
    def register(fn: Handler) -> Handler:
        for event in events:
            HANDLERS[event.value] = fn
        return fn

    return register


def local_time(value: datetime, tz: str) -> str:
    return value.astimezone(ZoneInfo(tz)).strftime("%a %d %b, %I:%M %p")


def booking_context(view: BookingView, settings: Settings) -> dict:
    b, tz = view.booking, view.listing.timezone
    return {
        "booking_id": str(b.id),
        "listing_title": view.listing.title,
        "address": f"{view.listing.address_line}, {view.listing.city}",
        "slot_label": view.slot.label,
        "starts_at": local_time(b.starts_at, tz),
        "ends_at": local_time(b.ends_at, tz),
        "driver_name": view.driver.full_name,
        "host_name": view.host.full_name,
        "currency": b.currency,
        "subtotal": f"{b.subtotal:.2f}",
        "tax_amount": f"{b.tax_amount + b.overstay_tax:.2f}",
        "overstay_fee": f"{b.overstay_fee:.2f}",
        "overstay_minutes": b.overstay_minutes,
        "total": f"{(b.final_amount if b.final_amount is not None else b.total_amount):.2f}",
        "payment_mode": b.payment_mode,
        "vehicle_number": b.vehicle_number or "",
        "booking_link": f"{settings.app_deep_link_base}bookings/{b.id}",
    }


async def _view(ctx: HandlerContext, payload: dict) -> BookingView:
    booking = await ctx.session.get(Booking, uuid.UUID(payload["booking_id"]))
    assert booking is not None, "booking referenced by event must exist"
    return await ctx.bookings.view(booking)


async def _notify(
    ctx: HandlerContext, user: User, event_id: str, title: str, body: str, data: dict, email: EmailSpec | None = None
) -> None:
    await ctx.notifications.deliver(
        user,
        type_=data["type"],
        title=title,
        body=body,
        data=data,
        dedupe_key=f"{event_id}:{user.id}",
        email=email,
    )


# ------------------------------------------------------------------ auth
@handles(Event.VERIFICATION_CODE)
async def on_verification_code(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    user = await ctx.session.get(User, uuid.UUID(payload["user_id"]))
    if user is None or user.status != "active":
        return
    template = "verify_email" if payload["purpose"] == "email_verify" else "reset_password"
    await ctx.email.send(
        to=user.email,
        template=template,
        context={"name": user.full_name, "code": payload["code"], "ttl_minutes": payload["ttl_minutes"]},
        dedupe_key=f"{event_id}:{template}",
        user_id=user.id,
    )


@handles(Event.PASSWORD_CHANGED)
async def on_password_changed(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    user = await ctx.session.get(User, uuid.UUID(payload["user_id"]))
    if user is None or user.status != "active":
        return
    await ctx.email.send(
        to=user.email,
        template="password_changed",
        context={"name": user.full_name},
        dedupe_key=f"{event_id}:password_changed",
        user_id=user.id,
    )


@handles(Event.ACCOUNT_DELETED)
async def on_account_deleted(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    await ctx.email.send(
        to=payload["email"],
        template="account_deleted",
        context={"name": payload["full_name"]},
        dedupe_key=f"{event_id}:account_deleted",
    )


@handles(Event.SUPPORT_REQUESTED)
async def on_support_requested(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    ticket = await ctx.session.get(SupportTicket, uuid.UUID(payload["ticket_id"]))
    if ticket is None:
        return
    s = ctx.settings
    context = {
        "ticket_id": str(ticket.id),
        "reference": str(ticket.id)[-8:].upper(),
        "name": ticket.name or "there",
        "email": ticket.email,
        "category": ticket.category,
        "subject": ticket.subject,
        "message": ticket.message,
        "booking_id": str(ticket.booking_id) if ticket.booking_id else None,
        "signed_in": ticket.user_id is not None,
    }
    # Each send has its own dedupe key, so a retry after one succeeded never repeats it.
    await ctx.email.send(
        to=s.support_email, template="support_request", context=context, dedupe_key=f"{event_id}:support_inbox"
    )
    await ctx.email.send(
        to=ticket.email,
        template="support_received",
        context=context,
        dedupe_key=f"{event_id}:support_ack",
        user_id=ticket.user_id,
    )


# ------------------------------------------------------------------ bookings
@handles(Event.BOOKING_REQUESTED)
async def on_requested(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    data = {"type": "booking_request", "booking_id": c["booking_id"]}
    await _notify(
        ctx,
        view.host,
        event_id,
        "New booking request",
        f"{view.driver.full_name} wants {view.listing.title} · {c['starts_at']}",
        data,
        EmailSpec("booking_request", c),
    )
    await _notify(
        ctx,
        view.driver,
        event_id,
        "Request sent",
        f"{view.listing.title} will confirm shortly",
        data | {"type": "booking_update"},
    )


@handles(Event.BOOKING_AWAITING_PAYMENT)
async def on_awaiting_payment(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    await _notify(
        ctx,
        view.driver,
        event_id,
        "Complete your payment",
        f"Pay {c['currency']} {c['total']} to secure {view.listing.title}",
        {"type": "booking_update", "booking_id": c["booking_id"]},
    )


@handles(Event.BOOKING_CONFIRMED)
async def on_confirmed(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    data = {"type": "booking_update", "booking_id": c["booking_id"]}
    await _notify(
        ctx,
        view.driver,
        event_id,
        "Booking confirmed",
        f"{view.listing.title} · slot {view.slot.label} · {c['starts_at']}",
        data,
        EmailSpec("booking_confirmed", c),
    )
    await _notify(
        ctx,
        view.host,
        event_id,
        "New booking",
        f"{view.driver.full_name} · slot {view.slot.label} · {c['starts_at']}",
        data,
    )


@handles(Event.BOOKING_REJECTED)
async def on_rejected(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    await _notify(
        ctx,
        view.driver,
        event_id,
        "Request declined",
        f"{view.listing.title} can't host you at {c['starts_at']}. Try another spot nearby.",
        {"type": "booking_update", "booking_id": c["booking_id"]},
        EmailSpec(
            "booking_status", c | {"headline": "Your request was declined", "detail": view.booking.cancel_reason or ""}
        ),
    )


@handles(Event.BOOKING_CANCELLED)
async def on_cancelled(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    refund = Decimal(payload.get("refund_amount", "0"))
    if refund > 0:
        await ctx.payments.refund_booking(view.booking.id, refund)
    c = booking_context(view, ctx.settings)
    data = {"type": "booking_update", "booking_id": c["booking_id"]}
    refund_text = f" A refund of {c['currency']} {refund:.2f} is on its way." if refund > 0 else ""
    by_host = payload.get("cancelled_by") == "host"
    await _notify(
        ctx,
        view.driver,
        event_id,
        "Booking cancelled",
        f"{view.listing.title} · {c['starts_at']}.{refund_text}",
        data,
        EmailSpec(
            "booking_status",
            c
            | {
                "headline": "Your booking was cancelled" + (" by the host" if by_host else ""),
                "detail": refund_text.strip(),
            },
        ),
    )
    await _notify(ctx, view.host, event_id, "Booking cancelled", f"{view.driver.full_name} · {c['starts_at']}", data)


@handles(Event.BOOKING_EXPIRED)
async def on_expired(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    if payload.get("reason") == "no_show":
        body = f"Your booking at {view.listing.title} ended without check-in."
    elif view.booking.approved_at is None:
        body = f"{view.listing.title} didn't respond in time. Try another spot nearby."
    else:
        body = f"The payment window for {view.listing.title} ran out."
    await _notify(
        ctx, view.driver, event_id, "Booking expired", body, {"type": "booking_update", "booking_id": c["booking_id"]}
    )


@handles(Event.BOOKING_CHECKED_IN)
async def on_checked_in(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    await _notify(
        ctx,
        view.driver,
        event_id,
        "You're checked in",
        f"Slot {view.slot.label} until {c['ends_at']}",
        {"type": "session", "booking_id": c["booking_id"]},
    )


@handles(Event.BOOKING_ENDING_SOON)
async def on_ending_soon(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    await _notify(
        ctx,
        view.driver,
        event_id,
        "Parking ends soon",
        f"Your time at {view.listing.title} ends at {c['ends_at']}. Overstay fees apply after that.",
        {"type": "session", "booking_id": c["booking_id"]},
    )


@handles(Event.BOOKING_COMPLETED)
async def on_completed(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    view = await _view(ctx, payload)
    c = booking_context(view, ctx.settings)
    data = {"type": "receipt", "booking_id": c["booking_id"]}
    await _notify(
        ctx,
        view.driver,
        event_id,
        "Thanks for parking",
        f"Total {c['currency']} {c['total']} · {view.listing.title}",
        data,
        EmailSpec("booking_receipt", c),
    )
    await _notify(
        ctx, view.host, event_id, "Booking completed", f"{view.driver.full_name} has left slot {view.slot.label}", data
    )


# ------------------------------------------------------------------ disputes
async def _admins(ctx: HandlerContext) -> list[User]:
    return list((await ctx.session.execute(select(User).where(User.is_admin, User.status == "active"))).scalars())


@handles(Event.DISPUTE_CREATED)
async def on_dispute_created(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    dispute = await ctx.session.get(Dispute, uuid.UUID(payload["dispute_id"]))
    assert dispute is not None
    reporter = await ctx.session.get(User, dispute.reporter_id)
    assert reporter is not None
    data = {"type": "dispute", "dispute_id": str(dispute.id), "booking_id": str(dispute.booking_id)}
    await _notify(ctx, reporter, event_id, "Report received", "Our team will review it and get back to you.", data)
    for admin in await _admins(ctx):
        await _notify(ctx, admin, event_id, "New dispute", f"{dispute.reason}: {dispute.description[:80]}", data)


@handles(Event.DISPUTE_UPDATED)
async def on_dispute_updated(ctx: HandlerContext, event_id: str, payload: dict) -> None:
    dispute = await ctx.session.get(Dispute, uuid.UUID(payload["dispute_id"]))
    assert dispute is not None
    reporter = await ctx.session.get(User, dispute.reporter_id)
    assert reporter is not None
    await _notify(
        ctx,
        reporter,
        event_id,
        "Update on your report",
        f"Status: {dispute.status.replace('_', ' ')}. {dispute.resolution or ''}".strip(),
        {"type": "dispute", "dispute_id": str(dispute.id), "booking_id": str(dispute.booking_id)},
        EmailSpec(
            "dispute_update",
            {"name": reporter.full_name, "status": dispute.status, "resolution": dispute.resolution or ""},
        ),
    )
