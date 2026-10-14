"""ORM mappings. The schema itself is owned by Alembic (migrations/versions)."""

import uuid
from datetime import datetime, time
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, TSTZRANGE, UUID, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk

MONEY = Numeric(12, 2)


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    avatar_key: Mapped[str | None] = mapped_column(Text)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="active")
    is_host: Mapped[bool] = mapped_column(Boolean, default=False)
    is_commercial_host: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(UUIDPk, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VerificationCode(UUIDPk, Base):
    __tablename__ = "verification_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    purpose: Mapped[str] = mapped_column(String(32))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PushToken(UUIDPk, Base):
    __tablename__ = "push_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(Text, unique=True)
    platform: Mapped[str] = mapped_column(String(16))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool] = mapped_column(JSONB)
    description: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Listing(UUIDPk, Timestamps, Base):
    __tablename__ = "listings"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    access_instructions: Mapped[str | None] = mapped_column(Text)
    address_line: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(80))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    latitude: Mapped[float] = mapped_column(Double)
    longitude: Mapped[float] = mapped_column(Double)
    location: Mapped[object] = mapped_column(
        Geography("POINT", 4326, spatial_index=False),
        Computed("ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography"),
        deferred=True,
    )
    timezone: Mapped[str] = mapped_column(String(64))
    amenities: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    hourly_rate: Mapped[Decimal] = mapped_column(MONEY)
    daily_cap: Mapped[Decimal | None] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(3))
    auto_accept: Mapped[bool] = mapped_column(Boolean, default=True)
    is_24h: Mapped[bool] = mapped_column(Boolean, default=True)
    open_time: Mapped[time | None] = mapped_column(Time)
    close_time: Mapped[time | None] = mapped_column(Time)
    open_days: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger), default=list)
    rating_avg: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    slots: Mapped[list["Slot"]] = relationship(back_populates="listing", order_by="Slot.label", lazy="raise")
    media: Mapped[list["ListingMedia"]] = relationship(
        back_populates="listing", order_by="ListingMedia.position", lazy="raise"
    )


class Slot(UUIDPk, Timestamps, Base):
    __tablename__ = "slots"

    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(32))
    floor: Mapped[str | None] = mapped_column(String(16))
    slot_type: Mapped[str] = mapped_column(String(16))
    hourly_rate_override: Mapped[Decimal | None] = mapped_column(MONEY)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    listing: Mapped[Listing] = relationship(back_populates="slots", lazy="raise")


class Upload(UUIDPk, Base):
    __tablename__ = "uploads"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    purpose: Mapped[str] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ListingMedia(UUIDPk, Base):
    __tablename__ = "listing_media"

    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    listing: Mapped[Listing] = relationship(back_populates="media", lazy="raise")


class Booking(UUIDPk, Timestamps, Base):
    __tablename__ = "bookings"

    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    host_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("slots.id", ondelete="RESTRICT"))
    period: Mapped[Range[datetime]] = mapped_column(TSTZRANGE)
    status: Mapped[str] = mapped_column(String(24))
    payment_mode: Mapped[str] = mapped_column(String(16))
    vehicle_number: Mapped[str | None] = mapped_column(String(16))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3))
    hourly_rate: Mapped[Decimal] = mapped_column(MONEY)
    subtotal: Mapped[Decimal] = mapped_column(MONEY)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY)
    platform_fee: Mapped[Decimal] = mapped_column(MONEY)
    total_amount: Mapped[Decimal] = mapped_column(MONEY)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overstay_minutes: Mapped[int] = mapped_column(Integer, default=0)
    overstay_fee: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    overstay_tax: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    final_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def starts_at(self) -> datetime:
        return self.period.lower  # type: ignore[return-value]

    @property
    def ends_at(self) -> datetime:
        return self.period.upper  # type: ignore[return-value]


class Payment(UUIDPk, Timestamps, Base):
    __tablename__ = "payments"

    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"))
    provider: Mapped[str] = mapped_column(String(16))
    provider_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    refunded_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16))
    failure_reason: Mapped[str | None] = mapped_column(Text)


class LedgerEntry(UUIDPk, Base):
    __tablename__ = "ledger_entries"

    txn_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id"))
    account: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(3))
    memo: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Notification(UUIDPk, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OutboxEvent(UUIDPk, Base):
    __tablename__ = "outbox_events"

    type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)


class EmailLog(UUIDPk, Timestamps, Base):
    __tablename__ = "email_log"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    to_email: Mapped[str] = mapped_column(CITEXT)
    template: Mapped[str] = mapped_column(String(64))
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text)


class EmailSuppression(Base):
    __tablename__ = "email_suppressions"

    email: Mapped[str] = mapped_column(CITEXT, primary_key=True)
    reason: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WebhookEvent(UUIDPk, Base):
    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(String(16))
    event_id: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    channel: Mapped[str] = mapped_column(String(16), primary_key=True)
    category: Mapped[str] = mapped_column(String(24), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Dispute(UUIDPk, Timestamps, Base):
    __tablename__ = "disputes"

    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"))
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)
    evidence_keys: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    status: Mapped[str] = mapped_column(String(16))
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class SupportTicket(UUIDPk, Timestamps, Base):
    __tablename__ = "support_tickets"

    # Null when sent from the sign-in screen (people who cannot log in need help the most).
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    email: Mapped[str] = mapped_column(CITEXT)
    name: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16))
