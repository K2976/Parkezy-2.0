"""Transactional outbox. Domain events are written in the SAME transaction as the state
change, so an event exists if and only if the change committed. Workers deliver them."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.db.models import OutboxEvent

OUTBOX_DIRTY = "outbox_dirty"


class Event(StrEnum):
    VERIFICATION_CODE = "auth.verification_code"
    PASSWORD_CHANGED = "auth.password_changed"
    BOOKING_REQUESTED = "booking.requested"
    BOOKING_AWAITING_PAYMENT = "booking.awaiting_payment"
    BOOKING_CONFIRMED = "booking.confirmed"
    BOOKING_REJECTED = "booking.rejected"
    BOOKING_CANCELLED = "booking.cancelled"
    BOOKING_EXPIRED = "booking.expired"
    BOOKING_CHECKED_IN = "booking.checked_in"
    BOOKING_COMPLETED = "booking.completed"
    BOOKING_ENDING_SOON = "booking.ending_soon"
    DISPUTE_CREATED = "dispute.created"
    DISPUTE_UPDATED = "dispute.updated"
    ACCOUNT_DELETED = "account.deleted"
    SUPPORT_REQUESTED = "support.requested"


class Outbox:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def add(self, event: Event, payload: dict, available_at: datetime | None = None) -> None:
        now = self._clock.now()
        self._session.add(
            OutboxEvent(
                type=event.value,
                payload=payload,
                created_at=now,
                available_at=available_at or now,
                attempts=0,
            )
        )
        # Picked up by the after-commit hook in app/api/deps.py to wake a worker immediately.
        self._session.info[OUTBOX_DIRTY] = True
