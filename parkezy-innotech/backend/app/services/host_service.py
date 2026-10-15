from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.db.models import Booking, LedgerEntry, Listing, User
from app.domain.enums import BookingStatus, LedgerAccount, ListingStatus


class HostDashboardService:
    """Numbers come from the ledger and bookings tables only — never estimated."""

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def _earnings_since(self, host: User, since) -> Decimal:
        query = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.user_id == host.id,
            LedgerEntry.account == LedgerAccount.HOST_PAYABLE.value,
            LedgerEntry.booking_id.is_not(None),  # earnings only; payouts move money, they don't un-earn it
        )
        if since is not None:
            query = query.where(LedgerEntry.created_at >= since)
        return -Decimal(await self._session.scalar(query))

    async def summary(self, host: User, *, days: int) -> dict:
        now = self._clock.now()
        counts = dict(
            (
                await self._session.execute(
                    select(Booking.status, func.count()).where(Booking.host_id == host.id).group_by(Booking.status)
                )
            ).all()
        )
        listings = await self._session.scalar(
            select(func.count()).where(Listing.owner_id == host.id, Listing.status == ListingStatus.ACTIVE.value)
        )
        daily = (
            await self._session.execute(
                select(func.date_trunc("day", LedgerEntry.created_at).label("day"), -func.sum(LedgerEntry.amount))
                .where(
                    LedgerEntry.user_id == host.id,
                    LedgerEntry.account == LedgerAccount.HOST_PAYABLE.value,
                    LedgerEntry.booking_id.is_not(None),
                    LedgerEntry.created_at >= now - timedelta(days=days),
                )
                .group_by("day")
                .order_by("day")
            )
        ).all()
        return {
            "active_listings": int(listings or 0),
            "pending_requests": int(counts.get(BookingStatus.PENDING_APPROVAL.value, 0)),
            "upcoming_bookings": int(counts.get(BookingStatus.CONFIRMED.value, 0)),
            "parked_now": int(counts.get(BookingStatus.CHECKED_IN.value, 0)),
            "completed_bookings": int(counts.get(BookingStatus.COMPLETED.value, 0)),
            "earnings_total": await self._earnings_since(host, None),
            "earnings_period": await self._earnings_since(host, now - timedelta(days=days)),
            "period_days": days,
            "daily_earnings": [{"day": d.date().isoformat(), "amount": Decimal(a)} for d, a in daily],
        }
