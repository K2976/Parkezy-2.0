"""Online payments (Razorpay). A booking is confirmed only after the server has verified a
payment, via the checkout signature or the webhook, whichever arrives first."""

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import Conflict, ExternalServiceError, Forbidden, NotFound, Unauthorized
from app.db.models import Booking, Payment, User, WebhookEvent
from app.domain.enums import BookingStatus, PaymentStatus
from app.infra.bloom import BloomFilter
from app.integrations.payments import GatewayOrder, PaymentGateway, to_minor_units
from app.services.booking_service import BookingService
from app.services.jobs import JobQueue

log = logging.getLogger(__name__)

PAYABLE_STATUSES = (BookingStatus.PENDING_PAYMENT.value, BookingStatus.COMPLETED.value)
# Already-confirmed bookings only owe money after an extension; otherwise there is nothing to pay.
TOP_UP_STATUSES = (BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value)


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        gateway: PaymentGateway | None,
        bookings: BookingService,
        clock: Clock,
        webhook_bloom: BloomFilter,
        jobs: JobQueue,
    ) -> None:
        self._session = session
        self._gateway = gateway
        self._bookings = bookings
        self._clock = clock
        self._bloom = webhook_bloom
        self._jobs = jobs

    def _require_gateway(self) -> PaymentGateway:
        if self._gateway is None:
            raise Conflict("Online payments are not enabled; pay at the venue", code="payments_disabled")
        return self._gateway

    async def _locked_booking(self, booking_id: uuid.UUID) -> Booking:
        booking = (
            await self._session.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
        ).scalar_one_or_none()
        if booking is None:
            raise NotFound("Booking not found")
        return booking

    async def _paid_total(self, booking_id: uuid.UUID) -> Decimal:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)).where(
                Payment.booking_id == booking_id,
                Payment.status.in_([PaymentStatus.CAPTURED.value, PaymentStatus.REFUNDED.value]),
            )
        )
        return Decimal(total)

    async def create_order(self, driver: User, booking_id: uuid.UUID) -> tuple[GatewayOrder, Booking]:
        gateway = self._require_gateway()
        booking = await self._locked_booking(booking_id)
        if booking.driver_id != driver.id:
            raise NotFound("Booking not found")
        if booking.status not in PAYABLE_STATUSES + TOP_UP_STATUSES:
            raise Conflict("Nothing to pay for this booking", code="not_payable")
        if booking.status == BookingStatus.PENDING_PAYMENT.value and booking.hold_expires_at <= self._clock.now():
            raise Conflict("The reservation hold has expired, please book again", code="hold_expired")
        target = booking.final_amount if booking.final_amount is not None else booking.total_amount
        due = target - await self._paid_total(booking.id)
        if booking.status in TOP_UP_STATUSES and due <= 0:
            raise Conflict("Nothing to pay for this booking", code="not_payable")
        if due <= 0:
            raise Conflict("This booking is already paid", code="already_paid")
        existing = (
            await self._session.execute(
                select(Payment).where(
                    Payment.booking_id == booking.id,
                    Payment.status == PaymentStatus.CREATED.value,
                    Payment.amount == due,
                )
            )
        ).scalar_one_or_none()
        if existing:  # reuse the open order so a double tap does not create two
            await self._session.commit()
            return (
                GatewayOrder(
                    provider=existing.provider,
                    order_id=existing.provider_order_id,
                    amount_minor=to_minor_units(due),
                    currency=existing.currency,
                    public_key=gateway.public_key,
                ),
                booking,
            )
        order = await gateway.create_order(
            amount=due, currency=booking.currency, receipt=str(booking.id), notes={"booking_id": str(booking.id)}
        )
        self._session.add(
            Payment(
                booking_id=booking.id,
                provider=gateway.name,
                provider_order_id=order.order_id,
                amount=due,
                refunded_amount=Decimal("0"),
                currency=booking.currency,
                status=PaymentStatus.CREATED.value,
            )
        )
        await self._session.commit()
        return order, booking

    async def confirm_checkout(
        self, driver: User, booking_id: uuid.UUID, *, order_id: str, payment_id: str, signature: str
    ) -> Booking:
        gateway = self._require_gateway()
        if not gateway.verify_checkout_signature(order_id=order_id, payment_id=payment_id, signature=signature):
            raise Forbidden("Payment could not be verified", code="payment_signature_invalid")
        booking = await self._locked_booking(booking_id)
        if booking.driver_id != driver.id:
            raise NotFound("Booking not found")
        await self._capture(order_id, payment_id)
        await self._session.refresh(booking)
        return booking

    async def _capture(self, order_id: str, payment_id: str) -> None:
        booking_id = await self._session.scalar(select(Payment.booking_id).where(Payment.provider_order_id == order_id))
        if booking_id is None:
            log.warning("capture for unknown order %s", order_id)
            return
        # Lock order is always booking -> payment, matching every other path.
        booking = await self._locked_booking(booking_id)
        payment = (
            await self._session.execute(select(Payment).where(Payment.provider_order_id == order_id).with_for_update())
        ).scalar_one()
        if payment.status in (PaymentStatus.CAPTURED.value, PaymentStatus.REFUNDED.value):
            await self._session.commit()
            return  # already processed (webhook and checkout both report the same payment)
        payment.status = PaymentStatus.CAPTURED.value
        payment.provider_payment_id = payment_id
        await self._session.flush()
        ok = await self._bookings.mark_paid(booking, await self._paid_total(booking.id))
        await self._session.commit()
        if not ok:
            # Paid after the hold expired / booking was cancelled: give the money back.
            self._jobs.enqueue("refund_payment", str(payment.id), str(payment.amount))

    async def _fail(self, order_id: str, reason: str) -> None:
        payment = (
            await self._session.execute(select(Payment).where(Payment.provider_order_id == order_id).with_for_update())
        ).scalar_one_or_none()
        if payment and payment.status == PaymentStatus.CREATED.value:
            payment.status = PaymentStatus.FAILED.value
            payment.failure_reason = reason[:500]
            await self._session.commit()

    async def handle_webhook(self, *, body: bytes, signature: str, event_id: str, event: dict) -> None:
        gateway = self._require_gateway()
        if not gateway.verify_webhook_signature(body=body, signature=signature):
            raise Unauthorized("Invalid webhook signature", code="webhook_signature_invalid")
        # Bloom filter: "definitely new" skips the lookup; "maybe seen" is confirmed in SQL.
        if await self._bloom.might_contain(f"{gateway.name}:{event_id}"):
            seen = await self._session.scalar(
                select(func.count()).where(WebhookEvent.provider == gateway.name, WebhookEvent.event_id == event_id)
            )
            if seen:
                return
        inserted = await self._session.execute(
            insert(WebhookEvent)
            .values(
                provider=gateway.name,
                event_id=event_id,
                event_type=str(event.get("event", ""))[:64],
                received_at=self._clock.now(),
            )
            .on_conflict_do_nothing(constraint="uq_webhook_events_provider_event")
            .returning(WebhookEvent.id)
        )
        if inserted.scalar_one_or_none() is None:
            await self._session.rollback()
            return
        await self._session.commit()
        await self._bloom.add(f"{gateway.name}:{event_id}")

        kind = event.get("event")
        entity = event.get("payload", {}).get("payment", {}).get("entity", {})
        if kind == "payment.captured" and entity.get("order_id"):
            await self._capture(entity["order_id"], entity["id"])
        elif kind == "payment.failed" and entity.get("order_id"):
            await self._fail(entity["order_id"], entity.get("error_description") or "failed")

    async def reconcile(self, *, check_after: timedelta, abandon_after: timedelta, batch: int) -> dict[str, int]:
        """Reconciliation (ch. 26): payments still "created" after `check_after` may have
        succeeded or failed without us hearing (lost webhook, app killed mid-checkout).
        Ask the PSP and apply its answer; give up on orders nobody paid after `abandon_after`."""
        if self._gateway is None:
            return {"checked": 0, "captured": 0, "failed": 0}
        now = self._clock.now()
        stale = list(
            (
                await self._session.execute(
                    select(Payment.provider_order_id, Payment.created_at)
                    .where(Payment.status == PaymentStatus.CREATED.value, Payment.created_at <= now - check_after)
                    .order_by(Payment.created_at)
                    .limit(batch)
                )
            ).all()
        )
        captured = failed = 0
        for order_id, created_at in stale:
            try:
                attempts = await self._gateway.order_payments(order_id)
            except ExternalServiceError:
                log.warning("reconcile: PSP unavailable for %s", order_id)
                continue
            success = next((p for p in attempts if p.status == "captured"), None)
            if success:
                await self._capture(order_id, success.payment_id)
                captured += 1
            elif created_at <= now - abandon_after:
                reason = next((p.error for p in attempts if p.status == "failed" and p.error), None)
                await self._fail(order_id, reason or "abandoned: no successful payment")
                failed += 1
        return {"checked": len(stale), "captured": captured, "failed": failed}

    async def refund(self, payment_id: uuid.UUID, amount: Decimal) -> None:
        """Worker entry point. Idempotent: never refunds more than was captured."""
        gateway = self._require_gateway()
        payment = (
            await self._session.execute(select(Payment).where(Payment.id == payment_id).with_for_update())
        ).scalar_one_or_none()
        if payment is None or not payment.provider_payment_id:
            return
        refundable = payment.amount - payment.refunded_amount
        amount = min(amount, refundable)
        if amount <= 0:
            return
        await gateway.refund(payment_id=payment.provider_payment_id, amount=amount)
        payment.refunded_amount += amount
        payment.status = PaymentStatus.REFUNDED.value
        await self._session.commit()

    async def refund_booking(self, booking_id: uuid.UUID, target_total: Decimal) -> None:
        """Bring the booking's total refunded amount up to `target_total`. Re-running it
        (worker retries) never refunds more than the target."""
        if self._gateway is None or target_total <= 0:
            return
        payments = list(
            (
                await self._session.execute(
                    select(Payment)
                    .where(
                        Payment.booking_id == booking_id,
                        Payment.status.in_([PaymentStatus.CAPTURED.value, PaymentStatus.REFUNDED.value]),
                    )
                    .order_by(Payment.created_at.desc())
                )
            ).scalars()
        )
        remaining = target_total - sum((p.refunded_amount for p in payments), Decimal("0"))
        for payment in payments:
            if remaining <= 0:
                break
            portion = min(remaining, payment.amount - payment.refunded_amount)
            if portion > 0:
                await self.refund(payment.id, portion)
                remaining -= portion
