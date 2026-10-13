import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.deps import CurrentUser, RulesDep, ServicesDep, UserRateLimit, page_limit
from app.api.presenters import booking_out
from app.schemas.bookings import (
    AccessCredentialsOut,
    BookingCreate,
    BookingOut,
    CancelRequest,
    QuoteOut,
    QuoteRequest,
)
from app.schemas.common import Page

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
