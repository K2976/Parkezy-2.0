import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.deps import CurrentUser, RulesDep, ServicesDep, UserRateLimit, page_limit
from app.api.presenters import booking_out, receipt_out, review_out
from app.schemas.bookings import (
    AccessCredentialsOut,
    BookingCreate,
    BookingOut,
    CancelRequest,
    ExtendRequest,
    ExtensionQuoteOut,
    QuoteOut,
    QuoteRequest,
    ReceiptOut,
)
from app.schemas.common import Page
from app.schemas.reviews import ReviewCreate, ReviewOut

router = APIRouter(prefix="/bookings", tags=["bookings"])
booking_limit = Depends(UserRateLimit("bookings", "rate_limit_default_per_window"))


@router.post("/quote", response_model=QuoteOut)
async def quote(body: QuoteRequest, services: ServicesDep, rules: RulesDep) -> QuoteOut:
    q = await services.bookings().quote(
        listing_id=body.listing_id, slot_id=body.slot_id, starts_at=body.starts_at, ends_at=body.ends_at, rules=rules
    )
    return QuoteOut(
        listing_id=q.listing.id,
        slot_id=q.slot.id if q.slot else None,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        duration_minutes=q.price.duration_minutes,
        hourly_rate=q.price.hourly_rate,
        subtotal=q.price.subtotal,
        tax_rate=q.price.tax_rate,
        tax_amount=q.price.tax_amount,
        total=q.price.total,
        currency=q.price.currency,
        payment_mode=q.payment_mode,
        requires_approval=not q.listing.auto_accept,
        available=q.available,
    )


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED, dependencies=[booking_limit])
async def create_booking(
    body: BookingCreate,
    response: Response,
    user: CurrentUser,
    services: ServicesDep,
    rules: RulesDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
) -> BookingOut:
    view, created = await services.bookings().create(
        user,
        listing_id=body.listing_id,
        slot_id=body.slot_id,
        slot_type=body.slot_type.value if body.slot_type else None,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        vehicle_number=body.vehicle_number,
        idempotency_key=idempotency_key,
        rules=rules,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return booking_out(view, user)


@router.get("", response_model=Page[BookingOut])
async def my_bookings(
    user: CurrentUser,
    services: ServicesDep,
    rules: RulesDep,
    group: Annotated[str | None, Query(pattern="^(upcoming|active|past)$")] = None,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> Page[BookingOut]:
    views, next_cursor = await services.bookings().list_for(
        user, as_host=False, group=group, cursor=cursor, limit=page_limit(rules, limit)
    )
    return Page[BookingOut](items=[booking_out(v, user) for v in views], next_cursor=next_cursor)


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(booking_id: uuid.UUID, user: CurrentUser, services: ServicesDep) -> BookingOut:
    return booking_out(await services.bookings().get_for_participant(user, booking_id), user)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID, body: CancelRequest, user: CurrentUser, services: ServicesDep, rules: RulesDep
) -> BookingOut:
    return booking_out(await services.bookings().cancel(user, booking_id, body.reason, rules), user)


@router.get("/{booking_id}/access", response_model=AccessCredentialsOut)
async def access_credentials(
    booking_id: uuid.UUID, user: CurrentUser, services: ServicesDep, rules: RulesDep
) -> AccessCredentialsOut:
    return AccessCredentialsOut(**await services.bookings().access_credentials(user, booking_id, rules))


@router.post("/{booking_id}/check-out", response_model=BookingOut)
async def check_out(booking_id: uuid.UUID, user: CurrentUser, services: ServicesDep, rules: RulesDep) -> BookingOut:
    return booking_out(await services.bookings().driver_check_out(user, booking_id, rules), user)


# ------------------------------------------------------------------ extend
@router.post("/{booking_id}/extend/quote", response_model=ExtensionQuoteOut)
async def extension_quote(
    booking_id: uuid.UUID, body: ExtendRequest, user: CurrentUser, services: ServicesDep, rules: RulesDep
) -> ExtensionQuoteOut:
    q = await services.bookings().extension_quote(user, booking_id, body.ends_at, rules)
    return ExtensionQuoteOut(
        booking_id=q.booking.id,
        current_ends_at=q.booking.ends_at,
        new_ends_at=q.new_ends_at,
        additional_minutes=q.additional_minutes,
        subtotal=q.subtotal,
        tax_amount=q.tax_amount,
        total=q.total,
        currency=q.booking.currency,
        available=q.available,
    )


@router.post("/{booking_id}/extend", response_model=BookingOut, dependencies=[booking_limit])
async def extend(
    booking_id: uuid.UUID, body: ExtendRequest, user: CurrentUser, services: ServicesDep, rules: RulesDep
) -> BookingOut:
    """Move the end time later. Sending the current end time again is a no-op, so retries are safe."""
    return booking_out(await services.bookings().extend(user, booking_id, body.ends_at, rules), user)


# ------------------------------------------------------------------ review
@router.post("/{booking_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def review_booking(
    booking_id: uuid.UUID, body: ReviewCreate, user: CurrentUser, services: ServicesDep, rules: RulesDep
) -> ReviewOut:
    review = await services.reviews().create(user, booking_id, rating=body.rating, comment=body.comment, rules=rules)
    return review_out(review, user)


# ------------------------------------------------------------------ receipt
@router.get("/{booking_id}/receipt", response_model=ReceiptOut)
async def receipt(booking_id: uuid.UUID, user: CurrentUser, services: ServicesDep) -> ReceiptOut:
    return receipt_out(await services.receipts().get(user, booking_id))


@router.get(
    "/{booking_id}/receipt.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "Receipt as a PDF file"}},
)
async def receipt_pdf(booking_id: uuid.UUID, user: CurrentUser, services: ServicesDep) -> Response:
    receipts = services.receipts()
    doc = await receipts.get(user, booking_id)
    return Response(
        content=receipts.render_pdf(doc),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.receipt.invoice_number}.pdf"'},
    )
