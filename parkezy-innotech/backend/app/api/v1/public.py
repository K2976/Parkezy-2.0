"""Unauthenticated discovery endpoints: config and listing search/detail."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep, ReadServicesDep, RulesDep, ServicesDep
from app.api.presenters import listing_out, search_item
from app.core.errors import ValidationFailed
from app.domain.enums import Amenity, DisputeReason, ListingKind, SlotType
from app.schemas.listings import ListingOut, ListingSearchItem, ListingSearchParams
from app.schemas.misc import PublicConfigOut

router = APIRouter(tags=["discovery"])


@router.get("/config", response_model=PublicConfigOut)
async def public_config(rules: RulesDep, c: ContainerDep, services: ServicesDep) -> PublicConfigOut:
    return PublicConfigOut(
        **rules.model_dump(
            include={
                "currency",
                "gst_rate",
                "booking_step_minutes",
                "min_booking_minutes",
                "max_booking_minutes",
                "max_advance_days",
                "payment_hold_minutes",
                "free_cancellation_minutes",
                "late_cancellation_fee_rate",
                "overstay_grace_minutes",
                "overstay_block_minutes",
                "overstay_block_fee",
                "early_checkin_minutes",
                "min_listing_photos",
                "max_listing_photos",
                "max_slots_per_listing",
                "max_dispute_photos",
                "search_default_radius_km",
                "search_max_radius_km",
            }
        ),
        payment_mode=services.bookings().payment_mode,
        upload_max_bytes=c.settings.upload_max_bytes,
        upload_allowed_types=c.settings.upload_allowed_types,
        default_timezone=c.settings.default_timezone,
        amenities=[a.value for a in Amenity],
        slot_types=[s.value for s in SlotType],
        dispute_reasons=[r.value for r in DisputeReason],
    )


@router.get("/listings", response_model=list[ListingSearchItem])
async def search_listings(
    services: ReadServicesDep,
    rules: RulesDep,
    c: ContainerDep,
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius_km: Annotated[float | None, Query(gt=0)] = None,
    kind: ListingKind | None = None,
    amenities: Annotated[list[Amenity] | None, Query()] = None,
    slot_type: SlotType | None = None,
    max_hourly_rate: Annotated[Decimal | None, Query(gt=0)] = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    only_available: bool = False,
    sort: Annotated[str, Query(pattern="^(distance|price)$")] = "distance",
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> list[ListingSearchItem]:
    try:
        params = ListingSearchParams(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            kind=kind,
            amenities=amenities or [],
            slot_type=slot_type,
            max_hourly_rate=max_hourly_rate,
            starts_at=starts_at,
            ends_at=ends_at,
            only_available=only_available,
            sort=sort,
            limit=limit,
        )
    except ValueError as e:
        raise ValidationFailed(str(e)) from e
    rows = await services.listings().search(params, rules)
    return [search_item(dict(row), c.storage) for row in rows]


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: uuid.UUID,
    services: ReadServicesDep,
    c: ContainerDep,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> ListingOut:
    if (starts_at is None) != (ends_at is None) or (starts_at and ends_at and ends_at <= starts_at):
        raise ValidationFailed("Provide a valid starts_at and ends_at together")
    listings = services.listings()
    listing = await listings.get_public(listing_id)
    availability = await listings.slot_availability(listing, starts_at, ends_at) if starts_at and ends_at else None
    return listing_out(listing, await listings.host_of(listing), c.storage, availability=availability)
