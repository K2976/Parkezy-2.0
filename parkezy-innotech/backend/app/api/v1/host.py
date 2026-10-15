import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.deps import ContainerDep, HostUser, RulesDep, ServicesDep, UserRateLimit, page_limit
from app.api.presenters import booking_out, listing_out, payout_account_out, payout_out, review_out
from app.schemas.bookings import AccessVerifyOut, AccessVerifyRequest, BookingOut, RejectRequest
from app.schemas.common import Page
from app.schemas.listings import ListingCreate, ListingOut, ListingUpdate, SlotInput, SlotUpdate
from app.schemas.misc import HostDashboardOut, PhotoAttachRequest
from app.schemas.payouts import (
    PayoutAccountIn,
    PayoutAccountOut,
    PayoutBalanceOut,
    PayoutOut,
    PayoutRequestIn,
)
from app.schemas.reviews import ReviewOut, ReviewReply

router = APIRouter(prefix="/host", tags=["host"])
verify_limit = Depends(UserRateLimit("access_verify", "rate_limit_access_verify_per_window"))


def _out(listing, host, c) -> ListingOut:
    return listing_out(listing, host, c.storage, include_private=True, include_inactive_slots=True)


# ------------------------------------------------------------------ listings
@router.get("/listings", response_model=list[ListingOut])
async def my_listings(host: HostUser, services: ServicesDep, c: ContainerDep) -> list[ListingOut]:
    return [_out(x, host, c) for x in await services.listings().list_owned(host)]


@router.post("/listings", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    body: ListingCreate, host: HostUser, services: ServicesDep, rules: RulesDep, c: ContainerDep
) -> ListingOut:
    return _out(await services.listings().create(host, body, rules), host, c)


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def get_my_listing(listing_id: uuid.UUID, host: HostUser, services: ServicesDep, c: ContainerDep) -> ListingOut:
    return _out(await services.listings().get_owned(host, listing_id), host, c)


@router.patch("/listings/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: uuid.UUID, body: ListingUpdate, host: HostUser, services: ServicesDep, rules: RulesDep, c: ContainerDep
) -> ListingOut:
    return _out(await services.listings().update(host, listing_id, body, rules), host, c)


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(listing_id: uuid.UUID, host: HostUser, services: ServicesDep) -> None:
    """Remove a spot. Refused while it has upcoming or active bookings; past bookings keep their history."""
    await services.listings().archive(host, listing_id)


@router.post("/listings/{listing_id}/slots", response_model=ListingOut)
async def add_slots(
    listing_id: uuid.UUID,
    body: list[SlotInput],
    host: HostUser,
    services: ServicesDep,
    rules: RulesDep,
    c: ContainerDep,
) -> ListingOut:
    return _out(await services.listings().add_slots(host, listing_id, body, rules), host, c)


@router.patch("/listings/{listing_id}/slots/{slot_id}", response_model=ListingOut)
async def update_slot(
    listing_id: uuid.UUID,
    slot_id: uuid.UUID,
    body: SlotUpdate,
    host: HostUser,
    services: ServicesDep,
    c: ContainerDep,
) -> ListingOut:
    return _out(await services.listings().update_slot(host, listing_id, slot_id, body), host, c)


@router.delete("/listings/{listing_id}/slots/{slot_id}", response_model=ListingOut)
async def delete_slot(
    listing_id: uuid.UUID, slot_id: uuid.UUID, host: HostUser, services: ServicesDep, c: ContainerDep
) -> ListingOut:
    return _out(await services.listings().delete_slot(host, listing_id, slot_id), host, c)


@router.post("/listings/{listing_id}/photos", response_model=ListingOut)
async def add_photos(
    listing_id: uuid.UUID,
    body: PhotoAttachRequest,
    host: HostUser,
    services: ServicesDep,
    rules: RulesDep,
    c: ContainerDep,
) -> ListingOut:
    return _out(await services.listings().add_photos(host, listing_id, body.upload_ids, rules), host, c)


@router.delete("/listings/{listing_id}/photos/{media_id}", response_model=ListingOut)
async def remove_photo(
    listing_id: uuid.UUID,
    media_id: uuid.UUID,
    host: HostUser,
    services: ServicesDep,
    rules: RulesDep,
    c: ContainerDep,
) -> ListingOut:
    return _out(await services.listings().remove_photo(host, listing_id, media_id, rules), host, c)


# ------------------------------------------------------------------ bookings
@router.get("/bookings", response_model=Page[BookingOut])
async def host_bookings(
    host: HostUser,
    services: ServicesDep,
    rules: RulesDep,
    group: Annotated[str | None, Query(pattern="^(upcoming|active|past)$")] = None,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> Page[BookingOut]:
    views, next_cursor = await services.bookings().list_for(
        host, as_host=True, group=group, cursor=cursor, limit=page_limit(rules, limit)
    )
    return Page[BookingOut](items=[booking_out(v, host) for v in views], next_cursor=next_cursor)


@router.post("/bookings/{booking_id}/approve", response_model=BookingOut)
async def approve(booking_id: uuid.UUID, host: HostUser, services: ServicesDep, rules: RulesDep) -> BookingOut:
    return booking_out(await services.bookings().approve(host, booking_id, rules), host)


@router.post("/bookings/{booking_id}/reject", response_model=BookingOut)
async def reject(booking_id: uuid.UUID, body: RejectRequest, host: HostUser, services: ServicesDep) -> BookingOut:
    return booking_out(await services.bookings().reject(host, booking_id, body.reason), host)


@router.post("/access/verify", response_model=AccessVerifyOut, dependencies=[verify_limit])
async def verify_access(
    body: AccessVerifyRequest, host: HostUser, services: ServicesDep, rules: RulesDep
) -> AccessVerifyOut:
    action, view = await services.bookings().verify_access(
        host, qr_token=body.qr_token, listing_id=body.listing_id, pin=body.pin, rules=rules
    )
    return AccessVerifyOut(action=action, booking=booking_out(view, host))


# ------------------------------------------------------------------ dashboard
@router.get("/dashboard", response_model=HostDashboardOut)
async def dashboard(
    host: HostUser, services: ServicesDep, rules: RulesDep, days: Annotated[int, Query(ge=1, le=365)] = 30
) -> HostDashboardOut:
    summary = await services.host_dashboard().summary(host, days=days)
    return HostDashboardOut(**summary, currency=rules.currency)


# ------------------------------------------------------------------ reviews
@router.post("/reviews/{review_id}/reply", response_model=ReviewOut)
async def reply_to_review(review_id: uuid.UUID, body: ReviewReply, host: HostUser, services: ServicesDep) -> ReviewOut:
    reviews = services.reviews()
    review = await reviews.reply(host, review_id, body.reply)
    authors = await reviews.authors([review])
    return review_out(review, authors.get(review.author_id))


# ------------------------------------------------------------------ payouts
@router.get("/payout-account", response_model=PayoutAccountOut)
async def get_payout_account(host: HostUser, services: ServicesDep) -> PayoutAccountOut:
    return payout_account_out(await services.payouts().account(host))


@router.put("/payout-account", response_model=PayoutAccountOut)
async def set_payout_account(body: PayoutAccountIn, host: HostUser, services: ServicesDep) -> PayoutAccountOut:
    return payout_account_out(await services.payouts().set_account(host, body.model_dump()))


@router.get("/payouts/balance", response_model=PayoutBalanceOut)
async def payout_balance(host: HostUser, services: ServicesDep, rules: RulesDep) -> PayoutBalanceOut:
    return PayoutBalanceOut(**await services.payouts().balance(host, rules))


@router.get("/payouts", response_model=Page[PayoutOut])
async def my_payouts(
    host: HostUser,
    services: ServicesDep,
    rules: RulesDep,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> Page[PayoutOut]:
    items, next_cursor = await services.payouts().list_for_host(host, cursor=cursor, limit=page_limit(rules, limit))
    return Page[PayoutOut](items=[payout_out(p) for p in items], next_cursor=next_cursor)


@router.post("/payouts", response_model=PayoutOut, status_code=status.HTTP_201_CREATED)
async def request_payout(
    body: PayoutRequestIn,
    response: Response,
    host: HostUser,
    services: ServicesDep,
    rules: RulesDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
) -> PayoutOut:
    payout, created = await services.payouts().request(host, body.amount, idempotency_key, rules)
    if not created:
        response.status_code = status.HTTP_200_OK
    return payout_out(payout)


@router.post("/payouts/{payout_id}/cancel", response_model=PayoutOut)
async def cancel_payout(payout_id: uuid.UUID, host: HostUser, services: ServicesDep) -> PayoutOut:
    return payout_out(await services.payouts().cancel(host, payout_id))
