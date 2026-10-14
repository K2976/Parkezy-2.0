"""Support tickets. Stored first (nothing is lost if email is down), then the outbox emails the
support inbox and acknowledges the sender, with at-least-once delivery and dedupe."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import NotFound
from app.db.models import Booking, SupportTicket, User
from app.domain.enums import SupportCategory, SupportStatus
from app.services.outbox import Event, Outbox


class SupportService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock
        self._outbox = Outbox(session, clock)

    async def create(
        self,
        user: User | None,
        *,
        email: str | None,
        name: str | None,
        category: SupportCategory,
        subject: str,
        message: str,
        booking_id: uuid.UUID | None,
    ) -> SupportTicket:
        if booking_id is not None:
            # Only link bookings the sender took part in; never confirm others exist.
            booking = await self._session.get(Booking, booking_id)
            if user is None or booking is None or user.id not in (booking.driver_id, booking.host_id):
                raise NotFound("Booking not found")
        ticket = SupportTicket(
            user_id=user.id if user else None,
            # A signed-in user's reply address is their verified account email, not a typed one.
            email=user.email if user else email,
            name=user.full_name if user else name,
            category=category.value,
            subject=subject,
            message=message,
            booking_id=booking_id,
            status=SupportStatus.OPEN.value,
        )
        self._session.add(ticket)
        await self._session.flush()
        self._outbox.add(Event.SUPPORT_REQUESTED, {"ticket_id": str(ticket.id)})
        await self._session.commit()
        return ticket

    async def list_mine(self, user: User, limit: int) -> list[SupportTicket]:
        query = (
            select(SupportTicket)
            .where(SupportTicket.user_id == user.id)
            .order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc())
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars())
