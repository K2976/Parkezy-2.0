import hashlib
import uuid
from datetime import datetime
from decimal import Decimal

import orjson
from geoalchemy2 import Geography
from sqlalchemy import Select, and_, cast, exists, func, literal, select
from sqlalchemy.dialects.postgresql import TSTZRANGE, Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.db.models import Booking, Listing, ListingMedia, Slot, User
from app.domain.availability import OpeningHours, is_within_hours
from app.domain.enums import BLOCKING_STATUSES, ListingKind, ListingStatus, UploadPurpose, UserStatus
from app.domain.geo import cell_for_search, haversine_m
from app.domain.rules import PlatformRules
from app.infra.cache import Cache
from app.integrations.storage import ObjectStorage
from app.schemas.listings import (
    ListingCreate,
    ListingSearchParams,
    ListingUpdate,
    SlotInput,
    SlotUpdate,
)
from app.services.upload_service import UploadService

LISTINGS_CACHE_NS = "listings"
ALL_DAYS = [1, 2, 3, 4, 5, 6, 7]


def opening_hours(listing: Listing) -> OpeningHours:
    return OpeningHours(
        timezone=listing.timezone,
        is_24h=listing.is_24h,
        open_time=listing.open_time,
        close_time=listing.close_time,
        open_days=tuple(listing.open_days),
    )


def window_range(starts_at: datetime, ends_at: datetime) -> Range:
    return Range(starts_at, ends_at, bounds="[)")


def slot_busy_clause(starts_at: datetime, ends_at: datetime):
    """SQL predicate: the outer `slots` row has a live booking overlapping the window."""
    return exists().where(
        Booking.slot_id == Slot.id,
        Booking.status.in_([s.value for s in BLOCKING_STATUSES]),
        Booking.period.op("&&")(literal(window_range(starts_at, ends_at), TSTZRANGE)),
    )


def owner_active_clause():
    """SQL predicate: the listing's host account is active (suspended hosts' spots are hidden)."""
    return exists().where(User.id == Listing.owner_id, User.status == UserStatus.ACTIVE.value)


def bookable_clause():
    """SQL predicate: drivers can see, save and book this listing."""
    return and_(Listing.status == ListingStatus.ACTIVE.value, owner_active_clause())


class ListingService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        clock: Clock,
        cache: Cache,
        storage: ObjectStorage,
        uploads: UploadService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._clock = clock
        self._cache = cache
        self._storage = storage
        self._uploads = uploads

    # ------------------------------------------------------------ loading
    def _full(self) -> Select:
        return select(Listing).options(selectinload(Listing.slots), selectinload(Listing.media))

    async def get(self, listing_id: uuid.UUID) -> Listing:
        listing = (await self._session.execute(self._full().where(Listing.id == listing_id))).scalar_one_or_none()
        if listing is None:
            raise NotFound("Listing not found")
        return listing

    async def _reload(self, listing_id: uuid.UUID) -> Listing:
        """Re-read a listing and its children after a write (refreshes cached collections)."""
        query = self._full().where(Listing.id == listing_id).execution_options(populate_existing=True)
        return (await self._session.execute(query)).scalar_one()

    async def get_public(self, listing_id: uuid.UUID) -> Listing:
        listing = (
            await self._session.execute(self._full().where(Listing.id == listing_id, bookable_clause()))
        ).scalar_one_or_none()
        if listing is None:
            raise NotFound("Listing not found")
        return listing

    async def get_owned(self, user: User, listing_id: uuid.UUID, *, lock: bool = False) -> Listing:
        """The host's own listing. Archived (deleted) listings are gone as far as the host is concerned."""
        if lock:
            # Row lock first: bookings take a share lock on the listing, so this waits for them.
            await self._session.execute(select(Listing.id).where(Listing.id == listing_id).with_for_update())
        listing = await self.get(listing_id)
        if listing.owner_id != user.id or listing.status == ListingStatus.ARCHIVED.value:
            raise NotFound("Listing not found")
        return listing

    async def list_owned(self, user: User) -> list[Listing]:
        result = await self._session.execute(
            self._full()
            .where(Listing.owner_id == user.id, Listing.status != ListingStatus.ARCHIVED.value)
            .order_by(Listing.created_at.desc())
        )
        return list(result.scalars())

    async def host_of(self, listing: Listing) -> User:
        host = await self._session.get(User, listing.owner_id)
        assert host is not None
        return host

    async def slot_availability(
        self, listing: Listing, starts_at: datetime, ends_at: datetime
    ) -> dict[uuid.UUID, bool]:
        open_ = is_within_hours(starts_at, ends_at, opening_hours(listing))
        busy = set(
            (
                await self._session.execute(
                    select(Slot.id).where(Slot.listing_id == listing.id, slot_busy_clause(starts_at, ends_at))
                )
            ).scalars()
        )
        return {s.id: open_ and s.is_active and s.id not in busy for s in listing.slots}

    def media_url(self, key: str) -> str:
        return self._storage.download_url(key)

    # ------------------------------------------------------------ host writes
    def _validate_hours(self, is_24h: bool, open_time, close_time) -> None:
        if not is_24h and (open_time is None or close_time is None or open_time >= close_time):
            raise ValidationFailed("Opening hours need open_time before close_time", code="invalid_hours")

    def _check_kind_allowed(self, user: User, kind: ListingKind) -> None:
        if not user.is_host:
            raise Forbidden("Become a host first", code="not_a_host")
        if kind == ListingKind.COMMERCIAL and not user.is_commercial_host:
            raise Forbidden("Commercial listings need an approved commercial account", code="not_commercial_host")

    async def create(self, user: User, data: ListingCreate, rules: PlatformRules) -> Listing:
        self._check_kind_allowed(user, data.kind)
        if len(data.slots) > rules.max_slots_per_listing:
            raise ValidationFailed("Too many slots", details={"max": rules.max_slots_per_listing})
        if len(data.photo_upload_ids) > rules.max_listing_photos:
            raise ValidationFailed("Too many photos", details={"max": rules.max_listing_photos})
        is_24h = True if data.is_24h is None else data.is_24h
        self._validate_hours(is_24h, data.open_time, data.close_time)
        photos = await self._uploads.require_uploaded(user, data.photo_upload_ids, UploadPurpose.LISTING_PHOTO)
        if data.publish and len(photos) < rules.min_listing_photos:
            raise ValidationFailed(
                "Add photos before publishing", code="photos_required", details={"min": rules.min_listing_photos}
            )
        listing = Listing(
            owner_id=user.id,
            kind=data.kind.value,
            status=(ListingStatus.ACTIVE if data.publish else ListingStatus.DRAFT).value,
            title=data.title,
            description=data.description,
            access_instructions=data.access_instructions,
            address_line=data.address_line,
            city=data.city,
            postal_code=data.postal_code,
            latitude=data.latitude,
            longitude=data.longitude,
            timezone=data.timezone or self._settings.default_timezone,
            amenities=[a.value for a in data.amenities or []],
            hourly_rate=data.hourly_rate,
            daily_cap=data.daily_cap,
            currency=rules.currency,
            auto_accept=True if data.auto_accept is None else data.auto_accept,
            is_24h=is_24h,
            open_time=None if is_24h else data.open_time,
            close_time=None if is_24h else data.close_time,
            open_days=data.open_days or ALL_DAYS,
            rating_count=0,
        )
        self._session.add(listing)
        await self._session.flush()
        for slot in data.slots:
            self._session.add(self._new_slot(listing.id, slot))
        self._attach_photos(listing.id, photos, start_position=0)
        await self._commit_listing_change()
        return await self._reload(listing.id)

    def _new_slot(self, listing_id: uuid.UUID, data: SlotInput) -> Slot:
        return Slot(
            listing_id=listing_id,
            label=data.label,
            floor=data.floor,
            slot_type=data.slot_type.value,
            hourly_rate_override=data.hourly_rate_override,
            is_active=True,
        )

    def _attach_photos(self, listing_id: uuid.UUID, photos, start_position: int) -> None:
        now = self._clock.now()
        for offset, upload in enumerate(photos):
            self._session.add(
                ListingMedia(
                    listing_id=listing_id,
                    upload_id=upload.id,
                    storage_key=upload.storage_key,
                    position=start_position + offset,
                    created_at=now,
                )
            )

    async def _commit_listing_change(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise Conflict("Duplicate slot label or photo", code="duplicate") from e
        await self._cache.bump(LISTINGS_CACHE_NS)

    async def update(self, user: User, listing_id: uuid.UUID, data: ListingUpdate, rules: PlatformRules) -> Listing:
        listing = await self.get_owned(user, listing_id, lock=data.status == ListingStatus.ARCHIVED)
        fields = data.model_dump(exclude_unset=True, exclude={"clear_daily_cap", "status", "amenities"})
        for name, value in fields.items():
            if value is not None:
                setattr(listing, name, value)
        if data.amenities is not None:
            listing.amenities = [a.value for a in data.amenities]
        if data.clear_daily_cap:
            listing.daily_cap = None
        if listing.is_24h:
            listing.open_time = listing.close_time = None
        self._validate_hours(listing.is_24h, listing.open_time, listing.close_time)
        if data.status is not None:
            await self._change_status(listing, data.status, rules)
        await self._commit_listing_change()
        return await self._reload(listing.id)

    async def archive(self, user: User, listing_id: uuid.UUID) -> None:
        """Delete a listing for good (soft: history and past bookings keep pointing at it)."""
        listing = await self.get_owned(user, listing_id, lock=True)
        await self._ensure_no_live_bookings(listing)
        listing.status = ListingStatus.ARCHIVED.value
        await self._commit_listing_change()

    async def _ensure_no_live_bookings(self, listing: Listing) -> None:
        live = await self._session.scalar(
            select(func.count()).where(
                Booking.listing_id == listing.id, Booking.status.in_([s.value for s in BLOCKING_STATUSES])
            )
        )
        if live:
            raise Conflict(
                "This spot has upcoming or active bookings. Cancel or finish them first.",
                code="listing_has_active_bookings",
                details={"active_bookings": int(live)},
            )

    async def _change_status(self, listing: Listing, status: ListingStatus, rules: PlatformRules) -> None:
        if status == ListingStatus.ARCHIVED:
            await self._ensure_no_live_bookings(listing)
        if status == ListingStatus.DRAFT and listing.status != ListingStatus.DRAFT.value:
            raise ValidationFailed("A published listing cannot go back to draft", code="invalid_status")
        if status == ListingStatus.ACTIVE:
            if len(listing.media) < rules.min_listing_photos:
                raise ValidationFailed(
                    "Add photos before publishing", code="photos_required", details={"min": rules.min_listing_photos}
                )
            if not any(s.is_active for s in listing.slots):
                raise ValidationFailed("Add at least one active slot", code="slots_required")
        listing.status = status.value

    async def add_slots(
        self, user: User, listing_id: uuid.UUID, slots: list[SlotInput], rules: PlatformRules
    ) -> Listing:
        listing = await self.get_owned(user, listing_id)
        if len(listing.slots) + len(slots) > rules.max_slots_per_listing:
            raise ValidationFailed("Too many slots", details={"max": rules.max_slots_per_listing})
        for slot in slots:
            self._session.add(self._new_slot(listing.id, slot))
        await self._commit_listing_change()
        return await self._reload(listing.id)

    async def update_slot(self, user: User, listing_id: uuid.UUID, slot_id: uuid.UUID, data: SlotUpdate) -> Listing:
        listing = await self.get_owned(user, listing_id)
        slot = next((s for s in listing.slots if s.id == slot_id), None)
        if slot is None:
            raise NotFound("Slot not found")
        for name in ("label", "floor", "is_active"):
            value = getattr(data, name)
            if value is not None:
                setattr(slot, name, value)
        if data.slot_type is not None:
            slot.slot_type = data.slot_type.value
        if data.hourly_rate_override is not None:
            slot.hourly_rate_override = data.hourly_rate_override
        if data.clear_rate_override:
            slot.hourly_rate_override = None
        await self._commit_listing_change()
        return await self._reload(listing.id)

    async def delete_slot(self, user: User, listing_id: uuid.UUID, slot_id: uuid.UUID) -> Listing:
        listing = await self.get_owned(user, listing_id)
        slot = next((s for s in listing.slots if s.id == slot_id), None)
        if slot is None:
            raise NotFound("Slot not found")
        has_bookings = await self._session.scalar(select(exists().where(Booking.slot_id == slot.id)))
        if has_bookings:
            slot.is_active = False  # keep history intact
        else:
            await self._session.delete(slot)
        await self._commit_listing_change()
        return await self._reload(listing.id)

    async def add_photos(
        self, user: User, listing_id: uuid.UUID, upload_ids: list[uuid.UUID], rules: PlatformRules
    ) -> Listing:
        listing = await self.get_owned(user, listing_id)
        if len(listing.media) + len(upload_ids) > rules.max_listing_photos:
            raise ValidationFailed("Too many photos", details={"max": rules.max_listing_photos})
        photos = await self._uploads.require_uploaded(user, upload_ids, UploadPurpose.LISTING_PHOTO)
        start = max((m.position for m in listing.media), default=-1) + 1
        self._attach_photos(listing.id, photos, start)
        await self._commit_listing_change()
        return await self._reload(listing.id)

    async def remove_photo(
        self, user: User, listing_id: uuid.UUID, media_id: uuid.UUID, rules: PlatformRules
    ) -> Listing:
        listing = await self.get_owned(user, listing_id)
        media = next((m for m in listing.media if m.id == media_id), None)
        if media is None:
            raise NotFound("Photo not found")
        if listing.status == ListingStatus.ACTIVE.value and len(listing.media) - 1 < rules.min_listing_photos:
            raise ValidationFailed("A live listing needs photos", code="photos_required")
        await self._session.delete(media)
        await self._commit_listing_change()
        return await self._reload(listing.id)

    # ------------------------------------------------------------ search
    async def search(self, params: ListingSearchParams, rules: PlatformRules) -> list[dict]:
        radius_km = params.radius_km or rules.search_default_radius_km
        if radius_km > rules.search_max_radius_km:
            raise ValidationFailed("Search radius too large", details={"max_km": rules.search_max_radius_km})
        limit = min(params.limit or rules.search_max_results, rules.search_max_results)
        radius_m = radius_km * 1000

        # Cache per geohash cell (shared by everyone nearby), then make it exact per request.
        cell = cell_for_search(params.latitude, params.longitude, radius_m, self._settings.search_cell_error_ratio)
        query_radius_m = radius_m + cell.half_diagonal_m
        candidate_limit = limit * self._settings.search_candidate_multiplier
        shared = params.model_dump(mode="json", exclude={"latitude", "longitude", "radius_km", "limit"})
        key_material = shared | {"cell": cell.geohash, "radius_m": round(query_radius_m), "candidates": candidate_limit}
        key = hashlib.sha256(orjson.dumps(key_material, option=orjson.OPT_SORT_KEYS)).hexdigest()

        async def load() -> list[dict]:
            return await self._search_db(params, cell.center_lat, cell.center_lng, query_radius_m, candidate_limit)

        candidates = await self._cache.get_or_set(
            LISTINGS_CACHE_NS, f"search:{key}", self._settings.search_cache_ttl_seconds, load
        )
        results = []
        for row in candidates:
            d = haversine_m(params.latitude, params.longitude, row["latitude"], row["longitude"])
            if d <= radius_m:
                results.append(row | {"distance_m": round(d, 1)})
        if params.sort == "price":
            results.sort(key=lambda r: (Decimal(r["hourly_rate"]), r["distance_m"], r["id"]))
        else:
            results.sort(key=lambda r: (r["distance_m"], r["id"]))
        return results[:limit]

    async def _search_db(
        self, params: ListingSearchParams, center_lat: float, center_lng: float, radius_m: float, limit: int
    ) -> list[dict]:
        point = cast(func.ST_SetSRID(func.ST_MakePoint(center_lng, center_lat), 4326), Geography)
        distance = func.ST_Distance(Listing.location, point).label("distance_m")

        total_slots = select(func.count()).where(Slot.listing_id == Listing.id, Slot.is_active).scalar_subquery()
        cover = (
            select(ListingMedia.storage_key)
            .where(ListingMedia.listing_id == Listing.id)
            .order_by(ListingMedia.position)
            .limit(1)
            .scalar_subquery()
        )
        columns = [Listing, distance, total_slots.label("total_slots"), cover.label("cover_key")]
        query = select(*columns).where(bookable_clause(), func.ST_DWithin(Listing.location, point, radius_m))
        if params.kind:
            query = query.where(Listing.kind == params.kind.value)
        if params.amenities:
            query = query.where(Listing.amenities.contains([a.value for a in params.amenities]))
        if params.max_hourly_rate is not None:
            query = query.where(Listing.hourly_rate <= params.max_hourly_rate)
        if params.slot_type:
            query = query.where(
                exists().where(
                    and_(Slot.listing_id == Listing.id, Slot.is_active, Slot.slot_type == params.slot_type.value)
                )
            )
        order = Listing.hourly_rate if params.sort == "price" else distance
        query = query.order_by(order, Listing.id).limit(limit)

        rows = (await self._session.execute(query)).all()
        free: dict[uuid.UUID, int] = {}
        if params.starts_at and params.ends_at and rows:
            free = await self._free_slot_counts(
                [row[0].id for row in rows], params.starts_at, params.ends_at, params.slot_type
            )
        results: list[dict] = []
        for row in rows:
            listing: Listing = row[0]
            available = free.get(listing.id, 0) if params.starts_at and params.ends_at else None
            if params.starts_at and params.ends_at:
                if not is_within_hours(params.starts_at, params.ends_at, opening_hours(listing)):
                    available = 0
                if params.only_available and not available:
                    continue
            results.append(
                {
                    "id": str(listing.id),
                    "kind": listing.kind,
                    "title": listing.title,
                    "address_line": listing.address_line,
                    "city": listing.city,
                    "latitude": listing.latitude,
                    "longitude": listing.longitude,
                    "hourly_rate": str(listing.hourly_rate),
                    "currency": listing.currency,
                    "amenities": list(listing.amenities),
                    "distance_m": round(float(row.distance_m), 1),
                    "total_slots": int(row.total_slots),
                    "available_slots": None if available is None else int(available),
                    "cover_key": row.cover_key,
                    "rating_avg": None if listing.rating_avg is None else str(listing.rating_avg),
                    "rating_count": listing.rating_count,
                }
            )
        return results

    async def _free_slot_counts(
        self, listing_ids: list[uuid.UUID], starts_at: datetime, ends_at: datetime, slot_type
    ) -> dict[uuid.UUID, int]:
        """Free active slots per listing in one round trip. Busy slots are found through the
        partial GiST index on bookings(listing_id, period) instead of one probe per slot."""
        busy = (
            select(Booking.slot_id)
            .where(
                Booking.listing_id.in_(listing_ids),
                Booking.status.in_([s.value for s in BLOCKING_STATUSES]),
                Booking.period.op("&&")(literal(window_range(starts_at, ends_at), TSTZRANGE)),
            )
            .scalar_subquery()
        )
        query = (
            select(Slot.listing_id, func.count())
            .where(Slot.listing_id.in_(listing_ids), Slot.is_active, Slot.id.not_in(busy))
            .group_by(Slot.listing_id)
        )
        if slot_type:
            query = query.where(Slot.slot_type == slot_type.value)
        return dict((await self._session.execute(query)).all())


def effective_rate(listing: Listing, slot: Slot) -> Decimal:
    return slot.hourly_rate_override or listing.hourly_rate
