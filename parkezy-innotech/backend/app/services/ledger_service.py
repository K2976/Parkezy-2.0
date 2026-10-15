"""Double-entry ledger. Positive = debit, negative = credit; each transaction sums to zero
(enforced again by a deferred trigger in the database)."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.db.models import Booking, LedgerEntry
from app.domain.enums import LedgerAccount, PaymentMode
from app.domain.pricing import money


class LedgerService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def _post(self, booking: Booking, memo: str, lines: list[tuple[LedgerAccount, uuid.UUID | None, Decimal]]) -> None:
        self._post_lines(booking.id, booking.currency, memo, lines)

    def _post_lines(
        self,
        booking_id: uuid.UUID | None,
        currency: str,
        memo: str,
        lines: list[tuple[LedgerAccount, uuid.UUID | None, Decimal]],
    ) -> None:
        if sum(amount for _, _, amount in lines) != 0:
            raise ValueError("Unbalanced ledger transaction")
        txn, now = uuid.uuid4(), self._clock.now()
        for account, user_id, amount in lines:
            if amount == 0:
                continue
            self._session.add(
                LedgerEntry(
                    txn_id=txn,
                    booking_id=booking_id,
                    account=account.value,
                    user_id=user_id,
                    amount=amount,
                    currency=currency,
                    memo=memo,
                    created_at=now,
                )
            )

    # ------------------------------------------------------------ payouts (no booking attached)
    # requested: host_payable is debited (the platform owes the host less) into payouts_pending.
    # paid:      payouts_pending is cleared against the platform's bank account.
    # returned:  rejected/cancelled requests move the money back to host_payable.
    def post_payout_requested(self, host_id: uuid.UUID, amount: Decimal, currency: str) -> None:
        self._post_lines(
            None,
            currency,
            "Payout requested",
            [(LedgerAccount.HOST_PAYABLE, host_id, amount), (LedgerAccount.PAYOUTS_PENDING, host_id, -amount)],
        )

    def post_payout_paid(self, host_id: uuid.UUID, amount: Decimal, currency: str) -> None:
        self._post_lines(
            None,
            currency,
            "Payout sent",
            [(LedgerAccount.PAYOUTS_PENDING, host_id, amount), (LedgerAccount.PLATFORM_BANK, None, -amount)],
        )

    def post_payout_returned(self, host_id: uuid.UUID, amount: Decimal, currency: str) -> None:
        self._post_lines(
            None,
            currency,
            "Payout returned",
            [(LedgerAccount.PAYOUTS_PENDING, host_id, amount), (LedgerAccount.HOST_PAYABLE, host_id, -amount)],
        )

    async def host_withdrawable(self, host_id: uuid.UUID) -> Decimal:
        """What the platform owes the host right now: earnings not yet withdrawn, minus cash the
        host already collected at the venue (which belongs partly to the platform and the taxman)."""
        total = await self._session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.user_id == host_id,
                LedgerEntry.account.in_([LedgerAccount.HOST_PAYABLE.value, LedgerAccount.HOST_COLLECTED.value]),
            )
        )
        return max(Decimal("0.00"), -Decimal(total or 0))

    def _cash_account(self, booking: Booking) -> tuple[LedgerAccount, uuid.UUID | None]:
        if booking.payment_mode == PaymentMode.PAY_AT_VENUE.value:
            return LedgerAccount.HOST_COLLECTED, booking.host_id
        return LedgerAccount.DRIVER_PAYMENTS, None

    def post_completion(self, booking: Booking) -> None:
        """Recognise revenue for a finished (or no-show) booking."""
        gross = booking.subtotal + booking.overstay_fee
        tax = booking.tax_amount + booking.overstay_tax
        fee = money(gross * booking.commission_rate)
        cash_account, cash_user = self._cash_account(booking)
        self._post(
            booking,
            "Booking completed",
            [
                (cash_account, cash_user, gross + tax),
                (LedgerAccount.GST_PAYABLE, None, -tax),
                (LedgerAccount.PLATFORM_REVENUE, None, -fee),
                (LedgerAccount.HOST_PAYABLE, booking.host_id, -(gross - fee)),
            ],
        )

    def post_cancellation_fee(self, booking: Booking, kept: Decimal) -> None:
        if kept <= 0:
            return
        fee = money(kept * booking.commission_rate)
        self._post(
            booking,
            "Late cancellation fee",
            [
                (LedgerAccount.DRIVER_PAYMENTS, None, kept),
                (LedgerAccount.PLATFORM_REVENUE, None, -fee),
                (LedgerAccount.HOST_PAYABLE, booking.host_id, -(kept - fee)),
            ],
        )

    async def host_earnings(self, host_id: uuid.UUID) -> Decimal:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.user_id == host_id,
                LedgerEntry.account == LedgerAccount.HOST_PAYABLE.value,
                LedgerEntry.booking_id.is_not(None),  # lifetime earnings; withdrawals don't reduce them
            )
        )
        return -Decimal(total)
