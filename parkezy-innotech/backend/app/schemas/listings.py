import uuid
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import available_timezones

from pydantic import Field, field_validator, model_validator

from app.domain.enums import Amenity, ListingKind, ListingStatus, SlotType
from app.schemas.common import Schema

_TIMEZONES = available_timezones()


class SlotInput(Schema):
    label: str = Field(min_length=1, max_length=32)
    floor: str | None = Field(default=None, max_length=16)
    slot_type: SlotType = SlotType.STANDARD
    hourly_rate_override: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class SlotUpdate(Schema):
    label: str | None = Field(default=None, min_length=1, max_length=32)
    floor: str | None = Field(default=None, max_length=16)
    slot_type: SlotType | None = None
    hourly_rate_override: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    clear_rate_override: bool = False
    is_active: bool | None = None


class HoursMixin(Schema):
    is_24h: bool | None = None
    open_time: time | None = None
    close_time: time | None = None
    open_days: list[int] | None = Field(default=None, min_length=1, max_length=7)

    @field_validator("open_days")
    @classmethod
    def _days(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if any(d < 1 or d > 7 for d in v):
            raise ValueError("open_days are ISO weekdays 1 (Mon) to 7 (Sun)")
        return sorted(set(v))


class ListingBase(HoursMixin):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    access_instructions: str | None = Field(default=None, max_length=2000)
    address_line: str | None = Field(default=None, min_length=3, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=80)
    postal_code: str | None = Field(default=None, max_length=16)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None
    amenities: list[Amenity] | None = None
    hourly_rate: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    daily_cap: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    auto_accept: bool | None = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        if v is not None and v not in _TIMEZONES:
            raise ValueError("Unknown IANA timezone")
        return v


class ListingCreate(ListingBase):
    kind: ListingKind = ListingKind.PRIVATE
    title: str = Field(min_length=3, max_length=120)
    address_line: str = Field(min_length=3, max_length=255)
    city: str = Field(min_length=2, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    hourly_rate: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    slots: list[SlotInput] = Field(min_length=1)
    photo_upload_ids: list[uuid.UUID] = Field(default_factory=list)
    publish: bool = True

    @model_validator(mode="after")
    def _check(self) -> "ListingCreate":
        labels = [s.label.lower() for s in self.slots]
        if len(labels) != len(set(labels)):
            raise ValueError("Slot labels must be unique")
        return self


class ListingUpdate(ListingBase):
    clear_daily_cap: bool = False
    status: ListingStatus | None = None


class MediaOut(Schema):
    id: uuid.UUID
    url: str
    position: int


class SlotOut(Schema):
    id: uuid.UUID
    label: str
    floor: str | None
    slot_type: SlotType
    hourly_rate: Decimal
    is_active: bool
    available: bool | None = None


class HostSummary(Schema):
    id: uuid.UUID
    first_name: str


class ListingOut(Schema):
    id: uuid.UUID
    kind: ListingKind
    status: ListingStatus
    title: str
    description: str | None
    address_line: str
    city: str
    postal_code: str | None
    latitude: float
    longitude: float
    timezone: str
    amenities: list[str]
    hourly_rate: Decimal
    daily_cap: Decimal | None
    currency: str
    auto_accept: bool
    is_24h: bool
    open_time: time | None
    close_time: time | None
    open_days: list[int]
    rating_avg: Decimal | None
    rating_count: int
    host: HostSummary
    slots: list[SlotOut]
    media: list[MediaOut]
    access_instructions: str | None = None  # only for the owner / confirmed drivers


class ListingSearchItem(Schema):
    id: uuid.UUID
    kind: ListingKind
    title: str
    address_line: str
    city: str
    latitude: float
    longitude: float
    hourly_rate: Decimal
    currency: str
    amenities: list[str]
    distance_m: float
    total_slots: int
    available_slots: int | None
    cover_photo_url: str | None
    rating_avg: Decimal | None


class ListingSearchParams(Schema):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0)
    kind: ListingKind | None = None
    amenities: list[Amenity] = Field(default_factory=list)
    slot_type: SlotType | None = None
    max_hourly_rate: Decimal | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    only_available: bool = False
    sort: str = Field(default="distance", pattern="^(distance|price)$")
    limit: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _window(self) -> "ListingSearchParams":
        if (self.starts_at is None) != (self.ends_at is None):
            raise ValueError("starts_at and ends_at must be given together")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.only_available and self.starts_at is None:
            raise ValueError("only_available requires starts_at and ends_at")
        return self
