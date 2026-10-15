"""Receipts / invoices for bookings that charged the driver something.

The invoice number is assigned once, on first issue, from a database sequence
(`PKZ-<year>-<6 digits>`): unique, increasing, and identical for the driver and the host."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import Conflict
from app.db.models import LedgerEntry, Receipt, User
from app.domain.enums import BookingStatus, LedgerAccount
from app.integrations import pdf
from app.services.booking_service import BookingService, BookingView

LATE_FEE_MEMO = "Late cancellation fee"


@dataclass(frozen=True)
class LineItem:
    kind: str  # parking | overstay | cancellation_fee | gst
    description: str
    amount: Decimal


@dataclass(frozen=True)
class ReceiptDoc:
    receipt: Receipt
    view: BookingView
    line_items: list[LineItem]
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal


def _hours(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h} h" + (f" {m} min" if m else "")


class ReceiptService:
    def __init__(self, session: AsyncSession, clock: Clock, bookings: BookingService, timezone: str) -> None:
        self._session = session
        self._clock = clock
        self._bookings = bookings
        self._tz = timezone

    async def _late_fee(self, booking_id: uuid.UUID) -> Decimal:
        kept = await self._session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.booking_id == booking_id,
                LedgerEntry.account == LedgerAccount.DRIVER_PAYMENTS.value,
                LedgerEntry.memo == LATE_FEE_MEMO,
            )
        )
        return Decimal(kept or 0)

    async def _lines(self, view: BookingView) -> tuple[list[LineItem], Decimal, Decimal, Decimal] | None:
        """(items, subtotal, tax, total), or None when nothing was charged."""
        b = view.booking
        if b.status == BookingStatus.COMPLETED.value or (
            b.status == BookingStatus.EXPIRED.value and b.final_amount is not None  # charged no-show
        ):
            minutes = int((b.ends_at - b.starts_at).total_seconds() // 60)
            items = [LineItem("parking", f"Parking, {_hours(minutes)} at {b.currency} {b.hourly_rate}/h", b.subtotal)]
            if b.overstay_fee > 0:
                items.append(LineItem("overstay", f"Overstay, {b.overstay_minutes} min", b.overstay_fee))
            tax = b.tax_amount + b.overstay_tax
            items.append(LineItem("gst", f"GST {b.tax_rate * 100:.0f}%", tax))
            subtotal = b.subtotal + b.overstay_fee
            return items, subtotal, tax, subtotal + tax
        if b.status == BookingStatus.CANCELLED.value:
            kept = await self._late_fee(b.id)
            if kept > 0:
                return [LineItem("cancellation_fee", "Late cancellation fee", kept)], kept, Decimal("0.00"), kept
        return None

    async def _issue(self, booking_id: uuid.UUID) -> Receipt:
        now = self._clock.now()
        year = now.astimezone(ZoneInfo(self._tz)).year
        # ON CONFLICT: the driver and host opening the receipt at the same moment get one number.
        await self._session.execute(
            text(
                "INSERT INTO receipts (booking_id, invoice_number, issued_at) "
                "VALUES (:booking_id, CAST(:prefix AS text) || lpad(nextval('invoice_number_seq')::text, 6, '0'), "
                ":issued_at) "
                "ON CONFLICT (booking_id) DO NOTHING"
            ),
            {"booking_id": booking_id, "prefix": f"PKZ-{year}-", "issued_at": now},
        )
        await self._session.commit()
        receipt = (await self._session.execute(select(Receipt).where(Receipt.booking_id == booking_id))).scalar_one()
        return receipt

    async def get(self, user: User, booking_id: uuid.UUID) -> ReceiptDoc:
        view = await self._bookings.get_for_participant(user, booking_id)
        lines = await self._lines(view)
        if lines is None:
            raise Conflict(
                "There's no receipt for this booking because nothing was charged",
                code="receipt_unavailable",
                details={"status": view.booking.status},
            )
        items, subtotal, tax, total = lines
        receipt = await self._issue(view.booking.id)
        if view.booking.status == BookingStatus.COMPLETED.value:
            paid, due = view.amount_paid, view.amount_due
        else:  # the fee or no-show charge was kept from what the driver paid
            paid, due = total, Decimal("0.00")
        return ReceiptDoc(receipt, view, items, subtotal, tax, total, paid, due)

    def render_pdf(self, doc: ReceiptDoc) -> bytes:
        b, listing, tz = doc.view.booking, doc.view.listing, ZoneInfo(doc.view.listing.timezone)

        def when(value: datetime | None) -> str:
            return value.astimezone(tz).strftime("%d %b %Y, %I:%M %p") if value else "-"

        cur = b.currency
        lines = [
            pdf.Line("Parkezy", size=20, bold=True),
            pdf.Line("Receipt / Tax invoice", size=13, bold=True, gap_before=6),
            pdf.Line(f"Invoice number: {doc.receipt.invoice_number}", gap_before=10),
            pdf.Line(f"Issued: {when(doc.receipt.issued_at)}"),
            pdf.Line(f"Booking: {b.id}"),
            pdf.Line("Parking spot", bold=True, gap_before=14),
            pdf.Line(listing.title),
            pdf.Line(f"{listing.address_line}, {listing.city}"),
            pdf.Line(f"Booked: {when(b.starts_at)} to {when(b.ends_at)}"),
            pdf.Line(f"Checked in: {when(b.checked_in_at)}   Checked out: {when(b.checked_out_at)}"),
            pdf.Line(f"Driver: {doc.view.driver.full_name}   Host: {doc.view.host.full_name}", gap_before=6),
            pdf.Line("Charges", bold=True, gap_before=14),
        ]
        lines += [pdf.Line(item.description, right=f"{cur} {item.amount:.2f}") for item in doc.line_items]
        lines += [
            pdf.Line("Total", bold=True, right=f"{cur} {doc.total:.2f}", gap_before=8),
            pdf.Line("Paid", right=f"{cur} {doc.amount_paid:.2f}"),
            pdf.Line("Balance due", right=f"{cur} {doc.amount_due:.2f}"),
            pdf.Line(
                "Paid online in the app." if b.payment_mode == "online" else "Paid to the host at the venue.",
                size=9,
                gap_before=18,
            ),
        ]
        return pdf.render(lines, title=f"Receipt {doc.receipt.invoice_number}")
