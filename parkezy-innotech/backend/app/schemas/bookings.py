import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.domain.enums import BookingStatus, PaymentMode, SlotType
from app.schemas.common import Schema


class WindowInput(Schema):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _order(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class QuoteRequest(WindowInput):
    listing_id: uuid.UUID
    slot_id: uuid.UUID | None = None


class QuoteOut(Schema):
    listing_id: uuid.UUID
    slot_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    hourly_rate: Decimal
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    payment_mode: PaymentMode
    requires_approval: bool
    available: bool


class BookingCreate(WindowInput):
    listing_id: uuid.UUID
    slot_id: uuid.UUID | None = Field(default=None, description="Omit to get any free slot")
    slot_type: SlotType | None = Field(default=None, description="Preferred type when slot_id is omitted")
    vehicle_number: str | None = Field(default=None, min_length=4, max_length=16)

    @field_validator("vehicle_number")
    @classmethod
    def _plate(cls, v: str | None) -> str | None:
        if v is None:
            return v
        cleaned = "".join(v.split()).upper()
        if not cleaned.isalnum():
            raise ValueError("Vehicle number may contain only letters and digits")
        return cleaned


class CancelRequest(Schema):
    reason: str | None = Field(default=None, max_length=500)


class RejectRequest(Schema):
    reason: str | None = Field(default=None, max_length=500)


class AccessVerifyRequest(Schema):
    qr_token: str | None = None
    listing_id: uuid.UUID | None = None
    pin: str | None = Field(default=None, pattern=r"^\d{4,8}$")

    @model_validator(mode="after")
    def _one(self):
        if not self.qr_token and not self.pin:
            raise ValueError("Provide either qr_token or pin")
        return self


class BookingListingOut(Schema):
    id: uuid.UUID
    title: str
    address_line: str
    city: str
    latitude: float
    longitude: float
    timezone: str


class BookingSlotOut(Schema):
    id: uuid.UUID
    label: str
    floor: str | None
    slot_type: SlotType


class PartyOut(Schema):
    id: uuid.UUID
    full_name: str
    phone: str | None = None


class BookingOut(Schema):
    id: uuid.UUID
    status: BookingStatus
    payment_mode: PaymentMode
    starts_at: datetime
    ends_at: datetime
    vehicle_number: str | None
    currency: str
    hourly_rate: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    overstay_minutes: int
    overstay_fee: Decimal
    overstay_tax: Decimal
    final_amount: Decimal | None
    amount_paid: Decimal
    amount_due: Decimal
    hold_expires_at: datetime | None
    approval_expires_at: datetime | None
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    listing: BookingListingOut
    slot: BookingSlotOut
    driver: PartyOut
    host: PartyOut
    access_instructions: str | None = None
    host_earnings: Decimal | None = None


class AccessCredentialsOut(Schema):
    booking_id: uuid.UUID
    pin: str
    qr_token: str
    qr_expires_at: datetime
    check_in_opens_at: datetime


class AccessVerifyOut(Schema):
    action: str  # "checked_in" | "checked_out"
    booking: BookingOut
