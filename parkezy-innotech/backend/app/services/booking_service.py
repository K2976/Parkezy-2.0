"""Booking engine. All money and availability decisions happen here, server-side.

Double booking is prevented by the database (exclusion constraint `ex_bookings_no_overlap`);
this service translates that violation into a clean 409 and, when the driver did not pick a
specific slot, retries with the next free one.
"""

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.security import TokenService
from app.db.models import Booking, Listing, Payment, Slot, User
from app.domain import booking_state
from app.domain.access import AccessCodeService
from app.domain.availability import ensure_within_hours, validate_window
from app.domain.enums import BookingStatus, ListingStatus, PaymentMode, PaymentStatus
from app.domain.pricing import PriceBreakdown, cancellation_fee, overstay, quote
from app.domain.rules import PlatformRules
from app.infra.cache import Cache
from app.infra.one_time import OneTimeTokenRegistry
from app.services.ledger_service import LedgerService
from app.services.listing_service import (
    LISTINGS_CACHE_NS,
    effective_rate,
    opening_hours,
    slot_busy_clause,
    window_range,
)
from app.services.outbox import Event, Outbox

QR_PURPOSE = "parking_access"
AUTO_PICK_RETRIES = 3
EXCLUSION_CONSTRAINT = "ex_bookings_no_overlap"
IDEMPOTENCY_CONSTRAINT = "uq_bookings_driver_idempotency"

UPCOMING = [BookingStatus.PENDING_APPROVAL, BookingStatus.PENDING_PAYMENT, BookingStatus.CONFIRMED]
ACTIVE = [BookingStatus.CHECKED_IN]
PAST = [BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.REJECTED, BookingStatus.EXPIRED]
STATUS_GROUPS = {"upcoming": UPCOMING, "active": ACTIVE, "past": PAST}


@dataclass
class BookingView:
    booking: Booking
    listing: Listing
    slot: Slot
    driver: User
    host: User
    amount_paid: Decimal

    @property
    def amount_due(self) -> Decimal:
        b = self.booking
        if b.status in (BookingStatus.CANCELLED, BookingStatus.REJECTED, BookingStatus.EXPIRED):
            return Decimal("0.00")
        target = b.final_amount if b.final_amount is not None else b.total_amount
        return max(Decimal("0.00"), target - self.amount_paid)


@dataclass(frozen=True)
class Quote:
    listing: Listing
    slot: Slot | None
    price: PriceBreakdown
    available: bool
    payment_mode: PaymentMode


def _encode_cursor(created_at: datetime, booking_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{booking_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        created, bid = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(created), uuid.UUID(bid)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValidationFailed("Invalid cursor", code="invalid_cursor") from e


def _constraint_name(error: IntegrityError) -> str | None:
    orig = getattr(error, "orig", None)
    name = getattr(orig, "constraint_name", None) or getattr(getattr(orig, "__cause__", None), "constraint_name", None)
    if name:
        return name
    text = str(orig)
    for candidate in (EXCLUSION_CONSTRAINT, IDEMPOTENCY_CONSTRAINT):
        if candidate in text:
            return candidate
    return None


class BookingService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        clock: Clock,
        cache: Cache,
        tokens: TokenService,
        access_codes: AccessCodeService,
        one_time: OneTimeTokenRegistry,
        online_payments: bool,
    ) -> None:
        self._session = session
        self._settings = settings
        self._clock = clock
        self._cache = cache
        self._tokens = tokens
        self._access = access_codes
        self._one_time = one_time
        self._online = online_payments
        self._outbox = Outbox(session, clock)
        self._ledger = LedgerService(session, clock)

    @property
    def payment_mode(self) -> PaymentMode:
        return PaymentMode.ONLINE if self._online else PaymentMode.PAY_AT_VENUE

    # ================================================================ reads
    async def _views(self, bookings: list[Booking]) -> list[BookingView]:
        if not bookings:
            return []
        listing_ids = {b.listing_id for b in bookings}
        slot_ids = {b.slot_id for b in bookings}
        user_ids = {b.driver_id for b in bookings} | {b.host_id for b in bookings}
        listings = {
            x.id: x for x in (await self._session.execute(select(Listing).where(Listing.id.in_(listing_ids)))).scalars()
        }
        slots = {x.id: x for x in (await self._session.execute(select(Slot).where(Slot.id.in_(slot_ids)))).scalars()}
        users = {x.id: x for x in (await self._session.execute(select(User).where(User.id.in_(user_ids)))).scalars()}
        paid_rows = await self._session.execute(
            select(Payment.booking_id, func.sum(Payment.amount - Payment.refunded_amount))
            .where(
                Payment.booking_id.in_([b.id for b in bookings]),
                Payment.status.in_([PaymentStatus.CAPTURED.value, PaymentStatus.REFUNDED.value]),
            )
            .group_by(Payment.booking_id)
        )
        paid = {bid: Decimal(total) for bid, total in paid_rows}
        views = []
        for b in bookings:
            amount_paid = paid.get(b.id, Decimal("0.00"))
            if b.payment_mode == PaymentMode.PAY_AT_VENUE.value and b.status == BookingStatus.COMPLETED.value:
                amount_paid = b.final_amount or b.total_amount  # settled with the host on exit
            views.append(
                BookingView(
                    b, listings[b.listing_id], slots[b.slot_id], users[b.driver_id], users[b.host_id], amount_paid
                )
            )
        return views

    async def view(self, booking: Booking) -> BookingView:
        return (await self._views([booking]))[0]

    async def _get(self, booking_id: uuid.UUID, *, lock: bool = False) -> Booking:
        query = select(Booking).where(Booking.id == booking_id)
        if lock:
            query = query.with_for_update()
        booking = (await self._session.execute(query)).scalar_one_or_none()
        if booking is None:
            raise NotFound("Booking not found")
        return booking

    async def get_for_participant(self, user: User, booking_id: uuid.UUID) -> BookingView:
        booking = await self._get(booking_id)
        if user.id not in (booking.driver_id, booking.host_id) and not user.is_admin:
            raise NotFound("Booking not found")
        return await self.view(booking)

    async def list_for(
        self, user: User, *, as_host: bool, group: str | None, cursor: str | None, limit: int
    ) -> tuple[list[BookingView], str | None]:
        owner_col = Booking.host_id if as_host else Booking.driver_id
        query = select(Booking).where(owner_col == user.id)
        if group:
            query = query.where(Booking.status.in_([s.value for s in STATUS_GROUPS[group]]))
        if cursor:
            created, bid = _decode_cursor(cursor)
            query = query.where(tuple_(Booking.created_at, Booking.id) < tuple_(created, bid))
        rows = list(
            (await self._session.execute(query.order_by(Booking.created_at.desc(), Booking.id.desc()).limit(limit + 1)))
            .scalars()
            .all()
        )
        next_cursor = _encode_cursor(rows[limit - 1].created_at, rows[limit - 1].id) if len(rows) > limit else None
        return await self._views(rows[:limit]), next_cursor

    # ================================================================ quote
    async def _load_bookable(self, listing_id: uuid.UUID) -> Listing:
        listing = await self._session.get(Listing, listing_id)
        if listing is None or listing.status != ListingStatus.ACTIVE.value:
            raise NotFound("Listing not found")
        return listing

    async def _load_slot(self, listing: Listing, slot_id: uuid.UUID) -> Slot:
        slot = await self._session.get(Slot, slot_id)
        if slot is None or slot.listing_id != listing.id or not slot.is_active:
            raise NotFound("Slot not found")
        return slot

    async def _free_slots(self, listing: Listing, starts_at: datetime, ends_at: datetime, slot_type: str | None):
        query = select(Slot).where(Slot.listing_id == listing.id, Slot.is_active, ~slot_busy_clause(starts_at, ends_at))
        if slot_type:
            query = query.where(Slot.slot_type == slot_type)
        return list((await self._session.execute(query.order_by(Slot.label))).scalars())

    def _price(self, listing: Listing, slot: Slot | None, starts_at, ends_at, rules: PlatformRules) -> PriceBreakdown:
        rate = effective_rate(listing, slot) if slot else listing.hourly_rate
        return quote(
            starts_at=starts_at,
            ends_at=ends_at,
            hourly_rate=rate,
            daily_cap=listing.daily_cap,
            tax_rate=rules.gst_rate,
            commission_rate=rules.commission_for(listing.kind),
            currency=listing.currency,
        )

    async def quote(
        self,
        *,
        listing_id: uuid.UUID,
        slot_id: uuid.UUID | None,
        starts_at: datetime,
        ends_at: datetime,
        rules: PlatformRules,
    ) -> Quote:
        validate_window(starts_at, ends_at, self._clock.now(), rules)
        listing = await self._load_bookable(listing_id)
        ensure_within_hours(starts_at, ends_at, opening_hours(listing))
        if slot_id:
            slot = await self._load_slot(listing, slot_id)
            free = {s.id for s in await self._free_slots(listing, starts_at, ends_at, None)}
            available = slot.id in free
        else:
            slot = None
            available = bool(await self._free_slots(listing, starts_at, ends_at, None))
        return Quote(listing, slot, self._price(listing, slot, starts_at, ends_at, rules), available, self.payment_mode)

    # ================================================================ create
    async def create(
        self,
        driver: User,
        *,
        listing_id: uuid.UUID,
        slot_id: uuid.UUID | None,
        slot_type: str | None,
        starts_at: datetime,
        ends_at: datetime,
        vehicle_number: str | None,
        idempotency_key: str,
        rules: PlatformRules,
    ) -> tuple[BookingView, bool]:
        """Returns (booking, created). Replaying the same Idempotency-Key returns the
        original booking with created=False instead of booking twice."""
        existing = await self._by_idempotency(driver, idempotency_key)
        if existing is not None:
            return await self._replay(existing, listing_id, starts_at, ends_at), False
        if driver.email_verified_at is None:
            raise Forbidden("Verify your email before booking", code="email_not_verified")
        now = self._clock.now()
        validate_window(starts_at, ends_at, now, rules)
        listing = await self._load_bookable(listing_id)
        if listing.owner_id == driver.id:
            raise Forbidden("You cannot book your own listing", code="own_listing")
        ensure_within_hours(starts_at, ends_at, opening_hours(listing))

        if slot_id:
            candidates = [await self._load_slot(listing, slot_id)]
        else:
            candidates = (await self._free_slots(listing, starts_at, ends_at, slot_type))[:AUTO_PICK_RETRIES]
            if not candidates:
                raise Conflict("No free slot for this time", code="no_availability")

        status = booking_state.status_after_request(auto_accept=listing.auto_accept, online_payment=self._online)
        for slot in candidates:
            price = self._price(listing, slot, starts_at, ends_at, rules)
            booking = Booking(
                driver_id=driver.id,
                host_id=listing.owner_id,
                listing_id=listing.id,
                slot_id=slot.id,
                period=window_range(starts_at, ends_at),
                status=status.value,
                payment_mode=self.payment_mode.value,
                vehicle_number=vehicle_number,
                idempotency_key=idempotency_key,
                currency=price.currency,
                hourly_rate=price.hourly_rate,
                subtotal=price.subtotal,
                tax_amount=price.tax_amount,
                platform_fee=price.platform_fee,
                total_amount=price.total,
                tax_rate=price.tax_rate,
                commission_rate=price.commission_rate,
                hold_expires_at=now + timedelta(minutes=rules.payment_hold_minutes)
                if status == BookingStatus.PENDING_PAYMENT
                else None,
                approval_expires_at=min(now + timedelta(minutes=rules.approval_timeout_minutes), starts_at)
                if status == BookingStatus.PENDING_APPROVAL
                else None,
                approved_at=now if listing.auto_accept else None,
                overstay_minutes=0,
                overstay_fee=Decimal("0"),
                overstay_tax=Decimal("0"),
            )
            try:
                # SAVEPOINT: a lost race only rolls back this insert, not the whole session.
                async with self._session.begin_nested():
                    self._session.add(booking)
            except IntegrityError as e:
                constraint = _constraint_name(e)
                if constraint == IDEMPOTENCY_CONSTRAINT:  # concurrent replay of the same request
                    replay = await self._by_idempotency(driver, idempotency_key)
                    assert replay is not None
                    return await self._replay(replay, listing_id, starts_at, ends_at), False
                if constraint != EXCLUSION_CONSTRAINT:
                    raise
                if slot_id:
                    raise Conflict("This slot was just booked for that time", code="slot_unavailable") from e
                continue  # someone took this slot a moment ago; try the next free one
            self._emit_created(booking, status)
            await self._session.commit()
            await self._cache.bump(LISTINGS_CACHE_NS)
            return await self.view(booking), True
        raise Conflict("No free slot for this time", code="no_availability")

    async def _by_idempotency(self, driver: User, key: str) -> Booking | None:
        return (
            await self._session.execute(
                select(Booking).where(Booking.driver_id == driver.id, Booking.idempotency_key == key)
            )
        ).scalar_one_or_none()

    async def _replay(self, booking: Booking, listing_id, starts_at, ends_at) -> BookingView:
        if booking.listing_id != listing_id or booking.starts_at != starts_at or booking.ends_at != ends_at:
            raise Conflict("Idempotency-Key was already used for a different booking", code="idempotency_mismatch")
        return await self.view(booking)

    def _emit_created(self, booking: Booking, status: BookingStatus) -> None:
        payload = {"booking_id": str(booking.id)}
        if status == BookingStatus.PENDING_APPROVAL:
            self._outbox.add(Event.BOOKING_REQUESTED, payload)
        elif status == BookingStatus.PENDING_PAYMENT:
            self._outbox.add(Event.BOOKING_AWAITING_PAYMENT, payload)
        else:
            self._outbox.add(Event.BOOKING_CONFIRMED, payload)

    # ================================================================ host decisions
    async def _get_hosted(self, host: User, booking_id: uuid.UUID) -> Booking:
        booking = await self._get(booking_id, lock=True)
        if booking.host_id != host.id:
            raise NotFound("Booking not found")
        return booking

    async def approve(self, host: User, booking_id: uuid.UUID, rules: PlatformRules) -> BookingView:
        booking = await self._get_hosted(host, booking_id)
        if booking.status != BookingStatus.PENDING_APPROVAL.value:
            raise Conflict("Only pending requests can be approved", code="invalid_booking_transition")
        now = self._clock.now()
        if booking.approval_expires_at and booking.approval_expires_at <= now:
            raise Conflict("This request has expired", code="request_expired")
        target = booking_state.status_after_approval(online_payment=self._online)
        booking_state.ensure_transition(booking.status, target)
        booking.status = target.value
        booking.approved_at = now
        booking.approval_expires_at = None
        if target == BookingStatus.PENDING_PAYMENT:
            booking.hold_expires_at = now + timedelta(minutes=rules.payment_hold_minutes)
            self._outbox.add(Event.BOOKING_AWAITING_PAYMENT, {"booking_id": str(booking.id)})
        else:
            self._outbox.add(Event.BOOKING_CONFIRMED, {"booking_id": str(booking.id)})
        await self._session.commit()
        return await self.view(booking)

    async def reject(self, host: User, booking_id: uuid.UUID, reason: str | None) -> BookingView:
        booking = await self._get_hosted(host, booking_id)
        booking_state.ensure_transition(booking.status, BookingStatus.REJECTED)
        booking.status = BookingStatus.REJECTED.value
        booking.cancel_reason = reason
        booking.cancelled_at = self._clock.now()
        self._outbox.add(Event.BOOKING_REJECTED, {"booking_id": str(booking.id)})
        await self._session.commit()
        await self._cache.bump(LISTINGS_CACHE_NS)
        return await self.view(booking)

    # ================================================================ payment hook
    async def mark_paid(self, booking: Booking, amount_paid_total: Decimal) -> bool:
        """Called by PaymentService (already holding the row lock). Returns False when the
        booking can no longer be confirmed, in which case the caller must refund."""
        if booking.status == BookingStatus.PENDING_PAYMENT.value:
            if amount_paid_total < booking.total_amount:
                return True  # partial; wait for the rest
            booking_state.ensure_transition(booking.status, BookingStatus.CONFIRMED)
            booking.status = BookingStatus.CONFIRMED.value
            booking.hold_expires_at = None
            self._outbox.add(Event.BOOKING_CONFIRMED, {"booking_id": str(booking.id)})
            return True
        return booking.status in (
            BookingStatus.CONFIRMED.value,
            BookingStatus.CHECKED_IN.value,
            BookingStatus.COMPLETED.value,
        )

    # ================================================================ cancel
    async def cancel(self, user: User, booking_id: uuid.UUID, reason: str | None, rules: PlatformRules) -> BookingView:
        booking = await self._get(booking_id, lock=True)
        is_driver, is_host = user.id == booking.driver_id, user.id == booking.host_id
        if not (is_driver or is_host):
            raise NotFound("Booking not found")
        booking_state.ensure_transition(booking.status, BookingStatus.CANCELLED)
        now = self._clock.now()
        view = await self.view(booking)
        paid = view.amount_paid
        kept = Decimal("0.00")
        # Hosts cancelling owe the driver everything; drivers pay a fee only when late.
        if is_driver and booking.status == BookingStatus.CONFIRMED.value and paid > 0:
            kept = min(
                paid,
                cancellation_fee(
                    subtotal=booking.subtotal,
                    minutes_before_start=(booking.starts_at - now).total_seconds() / 60,
                    free_minutes=rules.free_cancellation_minutes,
                    fee_rate=rules.late_cancellation_fee_rate,
                ),
            )
        booking.status = BookingStatus.CANCELLED.value
        booking.cancelled_at = now
        booking.cancel_reason = reason or ("Cancelled by host" if is_host else "Cancelled by driver")
        booking.hold_expires_at = None
        self._ledger.post_cancellation_fee(booking, kept)
        self._outbox.add(
            Event.BOOKING_CANCELLED,
            {
                "booking_id": str(booking.id),
                "cancelled_by": "host" if is_host else "driver",
                "refund_amount": str(paid - kept),
                "fee_kept": str(kept),
            },
        )
        await self._session.commit()
        await self._cache.bump(LISTINGS_CACHE_NS)
        return await self.view(booking)

    # ================================================================ access
    async def access_credentials(self, driver: User, booking_id: uuid.UUID, rules: PlatformRules) -> dict:
        booking = await self._get(booking_id)
        if booking.driver_id != driver.id:
            raise NotFound("Booking not found")
        if booking.status not in (BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value):
            raise Conflict("Access codes are available once the booking is confirmed", code="not_confirmed")
        now = self._clock.now()
        ttl = timedelta(seconds=self._settings.qr_token_ttl_seconds)
        token = self._tokens.encode(str(booking.id), QR_PURPOSE, now, ttl)
        return {
            "booking_id": booking.id,
            "pin": self._access.pin_for(booking.id),
            "qr_token": token,
            "qr_expires_at": now + ttl,
            "check_in_opens_at": booking.starts_at - timedelta(minutes=rules.early_checkin_minutes),
        }

    async def _booking_from_qr(self, token: str) -> Booking:
        payload = self._tokens.decode(token, QR_PURPOSE)
        if not await self._one_time.consume(QR_PURPOSE, payload["jti"], self._settings.qr_token_ttl_seconds):
            raise Forbidden("This code was already used; ask the driver to refresh it", code="qr_replayed")
        return await self._get(uuid.UUID(payload["sub"]), lock=True)

    async def _booking_from_pin(
        self, host: User, listing_id: uuid.UUID | None, pin: str, rules: PlatformRules
    ) -> Booking:
        """Match the PIN against every live booking at this host's spots (not only ones inside the check-in
        window), so the host learns WHY a correct PIN can't be used yet instead of "not recognised"."""
        now = self._clock.now()
        live = [
            BookingStatus.PENDING_APPROVAL.value,
            BookingStatus.PENDING_PAYMENT.value,
            BookingStatus.CONFIRMED.value,
            BookingStatus.CHECKED_IN.value,
        ]
        query = select(Booking).where(
            Booking.host_id == host.id,
            Booking.status.in_(live),
            # Bounded: today's and upcoming bookings, plus anyone still parked from earlier.
            or_(
                func.upper(Booking.period) > now - timedelta(hours=12), Booking.status == BookingStatus.CHECKED_IN.value
            ),
        )
        if listing_id:
            query = query.where(Booking.listing_id == listing_id)
        candidates = (await self._session.execute(query)).scalars()
        matches = [b for b in candidates if self._access.verify_pin(b.id, pin)]
        if not matches:
            raise Forbidden(
                "No booking at your spots matches this PIN. Check the digits, and that you're signed in "
                "as the host of this parking spot.",
                code="invalid_pin",
            )
        if len(matches) > 1:
            # Two 6-digit PINs colliding at one host is rare; prefer the one that can act right now.
            ready = [
                b
                for b in matches
                if b.status == BookingStatus.CHECKED_IN.value or self._in_checkin_window(b, now, rules)
            ]
            if len(ready) != 1:
                raise Conflict("This PIN matches more than one booking; choose the spot first", code="pin_ambiguous")
            matches = ready
        booking = matches[0]
        if booking.status == BookingStatus.PENDING_APPROVAL.value:
            raise Conflict(
                "This is a booking request you haven't approved yet. Approve it in Bookings, then check the driver in.",
                code="needs_approval",
                details={"booking_id": str(booking.id)},
            )
        if booking.status == BookingStatus.PENDING_PAYMENT.value:
            raise Conflict(
                "The driver hasn't paid for this booking yet; ask them to complete payment in the app.",
                code="awaiting_payment",
                details={"booking_id": str(booking.id)},
            )
        return await self._get(booking.id, lock=True)

    @staticmethod
    def _in_checkin_window(booking: Booking, now: datetime, rules: PlatformRules) -> bool:
        return (
            booking.status == BookingStatus.CONFIRMED.value
            and booking.starts_at - timedelta(minutes=rules.early_checkin_minutes) <= now < booking.ends_at
        )

    async def verify_access(
        self, host: User, *, qr_token: str | None, listing_id: uuid.UUID | None, pin: str | None, rules: PlatformRules
    ) -> tuple[str, BookingView]:
        if qr_token:
            booking = await self._booking_from_qr(qr_token)
        else:
            assert pin
            booking = await self._booking_from_pin(host, listing_id, pin, rules)
        if booking.host_id != host.id:
            raise Forbidden("This booking is for a different host", code="wrong_host")
        if booking.status == BookingStatus.CONFIRMED.value:
            return "checked_in", await self._check_in(booking, rules)
        if booking.status == BookingStatus.CHECKED_IN.value:
            return "checked_out", await self._check_out(booking, rules)
        raise Conflict(f"Booking is {booking.status}", code="not_checkin_eligible")

    async def _check_in(self, booking: Booking, rules: PlatformRules) -> BookingView:
        now = self._clock.now()
        opens_at = booking.starts_at - timedelta(minutes=rules.early_checkin_minutes)
        if now < opens_at:
            tz = ZoneInfo((await self._session.get(Listing, booking.listing_id)).timezone)
            raise Conflict(
                f"Too early to check in. Check-in opens at {opens_at.astimezone(tz):%I:%M %p on %d %b}.",
                code="too_early",
                details={"starts_at": booking.starts_at.isoformat(), "check_in_opens_at": opens_at.isoformat()},
            )
        if now >= booking.ends_at:
            raise Conflict("This booking has already ended, so it can't be checked in", code="booking_ended")
        booking_state.ensure_transition(booking.status, BookingStatus.CHECKED_IN)
        booking.status = BookingStatus.CHECKED_IN.value
        booking.checked_in_at = now
        self._outbox.add(Event.BOOKING_CHECKED_IN, {"booking_id": str(booking.id)})
        await self._session.commit()
        return await self.view(booking)

    async def _check_out(self, booking: Booking, rules: PlatformRules) -> BookingView:
        now = self._clock.now()
        charge = overstay(
            ends_at=booking.ends_at,
            checked_out_at=now,
            grace_minutes=rules.overstay_grace_minutes,
            block_minutes=rules.overstay_block_minutes,
            block_fee=rules.overstay_block_fee,
            tax_rate=booking.tax_rate,
        )
        booking_state.ensure_transition(booking.status, BookingStatus.COMPLETED)
        booking.status = BookingStatus.COMPLETED.value
        booking.checked_out_at = now
        booking.overstay_minutes = charge.minutes
        booking.overstay_fee = charge.fee
        booking.overstay_tax = charge.tax
        booking.final_amount = booking.total_amount + charge.fee + charge.tax
        self._ledger.post_completion(booking)
        self._outbox.add(Event.BOOKING_COMPLETED, {"booking_id": str(booking.id)})
        await self._session.commit()
        await self._cache.bump(LISTINGS_CACHE_NS)
        return await self.view(booking)

    async def driver_check_out(self, driver: User, booking_id: uuid.UUID, rules: PlatformRules) -> BookingView:
        booking = await self._get(booking_id, lock=True)
        if booking.driver_id != driver.id:
            raise NotFound("Booking not found")
        if booking.status != BookingStatus.CHECKED_IN.value:
            raise Conflict("You are not checked in", code="not_checked_in")
        return await self._check_out(booking, rules)

    # ================================================================ maintenance (worker)
    async def expire_stale(self) -> int:
        """Release holds that ran out and requests hosts never answered."""
        now = self._clock.now()
        rows = list(
            (
                await self._session.execute(
                    select(Booking)
                    .where(
                        or_(
                            and_(Booking.status == BookingStatus.PENDING_PAYMENT.value, Booking.hold_expires_at <= now),
                            and_(
                                Booking.status == BookingStatus.PENDING_APPROVAL.value,
                                Booking.approval_expires_at <= now,
                            ),
                        )
                    )
                    .with_for_update(skip_locked=True)
                    .limit(500)
                )
            ).scalars()
        )
        for booking in rows:
            booking.status = BookingStatus.EXPIRED.value
            booking.hold_expires_at = None
            self._outbox.add(Event.BOOKING_EXPIRED, {"booking_id": str(booking.id), "reason": "unanswered"})
        await self._session.commit()
        if rows:
            await self._cache.bump(LISTINGS_CACHE_NS)
        return len(rows)

    async def expire_no_shows(self) -> int:
        """Confirmed bookings whose window passed without check-in. Online payments are
        kept (the slot was reserved) and recognised in the ledger."""
        now = self._clock.now()
        rows = list(
            (
                await self._session.execute(
                    select(Booking)
                    .where(Booking.status == BookingStatus.CONFIRMED.value, func.upper(Booking.period) <= now)
                    .with_for_update(skip_locked=True)
                    .limit(500)
                )
            ).scalars()
        )
        for booking in rows:
            booking.status = BookingStatus.EXPIRED.value
            if booking.payment_mode == PaymentMode.ONLINE.value:
                booking.final_amount = booking.total_amount
                self._ledger.post_completion(booking)
            self._outbox.add(Event.BOOKING_EXPIRED, {"booking_id": str(booking.id), "reason": "no_show"})
        await self._session.commit()
        return len(rows)

    async def send_ending_reminders(self, rules: PlatformRules) -> int:
        now = self._clock.now()
        lead = timedelta(minutes=rules.reminder_minutes_before_end)
        rows = list(
            (
                await self._session.execute(
                    select(Booking)
                    .where(
                        Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value]),
                        Booking.reminder_sent_at.is_(None),
                        func.upper(Booking.period) <= now + lead,
                        func.upper(Booking.period) > now,
                    )
                    .with_for_update(skip_locked=True)
                    .limit(500)
                )
            ).scalars()
        )
        for booking in rows:
            booking.reminder_sent_at = now
            self._outbox.add(Event.BOOKING_ENDING_SOON, {"booking_id": str(booking.id)})
        await self._session.commit()
        return len(rows)
