import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.domain.enums import DisputeReason, DisputeStatus, PaymentMode, UploadPurpose
from app.schemas.common import Schema


class UploadRequest(Schema):
    purpose: UploadPurpose
    content_type: str = Field(max_length=64)


class UploadOut(Schema):
    id: uuid.UUID
    upload_url: str
    method: str
    headers: dict[str, str]
    expires_in: int
    max_bytes: int


class UploadCompleteOut(Schema):
    id: uuid.UUID
    status: str
    size_bytes: int | None


class PhotoAttachRequest(Schema):
    upload_ids: list[uuid.UUID] = Field(min_length=1)


class PaymentOrderOut(Schema):
    provider: str
    order_id: str
    amount_minor: int
    currency: str
    key_id: str
    booking_id: uuid.UUID
    description: str
    prefill_email: str
    prefill_phone: str | None


class PaymentConfirmRequest(Schema):
    order_id: str = Field(max_length=64)
    payment_id: str = Field(max_length=64)
    signature: str = Field(max_length=256)


class NotificationOut(Schema):
    id: uuid.UUID
    type: str
    title: str
    body: str
    data: dict
    read_at: datetime | None
    created_at: datetime


class NotificationList(Schema):
    items: list[NotificationOut]
    unread_count: int


class MarkReadRequest(Schema):
    ids: list[uuid.UUID] | None = None


class DisputeCreate(Schema):
    booking_id: uuid.UUID
    reason: DisputeReason
    description: str = Field(min_length=10, max_length=4000)
    evidence_upload_ids: list[uuid.UUID] = Field(default_factory=list)


class DisputeOut(Schema):
    id: uuid.UUID
    booking_id: uuid.UUID
    reason: DisputeReason
    description: str
    status: DisputeStatus
    resolution: str | None
    evidence_urls: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DisputeReview(Schema):
    status: DisputeStatus
    resolution: str | None = Field(default=None, max_length=4000)


class SettingOut(Schema):
    key: str
    value: Any
    description: str
    updated_at: datetime


class SettingsPatch(Schema):
    changes: dict[str, Any] = Field(min_length=1)


class PublicConfigOut(Schema):
    currency: str
    gst_rate: Decimal
    booking_step_minutes: int
    min_booking_minutes: int
    max_booking_minutes: int
    max_advance_days: int
    payment_mode: PaymentMode
    payment_hold_minutes: int
    free_cancellation_minutes: int
    late_cancellation_fee_rate: Decimal
    overstay_grace_minutes: int
    overstay_block_minutes: int
    overstay_block_fee: Decimal
    early_checkin_minutes: int
    min_listing_photos: int
    max_listing_photos: int
    max_slots_per_listing: int
    max_dispute_photos: int
    search_default_radius_km: float
    search_max_radius_km: float
    upload_max_bytes: int
    upload_allowed_types: list[str]
    default_timezone: str
    amenities: list[str]
    slot_types: list[str]
    dispute_reasons: list[str]


class DailyEarning(Schema):
    day: str
    amount: Decimal


class HostDashboardOut(Schema):
    active_listings: int
    pending_requests: int
    upcoming_bookings: int
    parked_now: int
    completed_bookings: int
    earnings_total: Decimal
    earnings_period: Decimal
    period_days: int
    daily_earnings: list[DailyEarning]
    currency: str


class OutboxEventOut(Schema):
    id: uuid.UUID
    type: str
    attempts: int
    last_error: str | None
    created_at: datetime
    available_at: datetime


class QueueStatsOut(Schema):
    pending: int
    dead: int
