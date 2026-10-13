"""Typed view of the `platform_settings` table. There are no defaults here on purpose:
every value must come from the database (seeded by migration 0001, editable by admins)."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlatformRules(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    currency: str = Field(min_length=3, max_length=3)
    gst_rate: Decimal = Field(ge=0, lt=1)
    commission_rate_private: Decimal = Field(ge=0, lt=1)
    commission_rate_commercial: Decimal = Field(ge=0, lt=1)
    booking_step_minutes: int = Field(gt=0, le=60)
    min_booking_minutes: int = Field(gt=0)
    max_booking_minutes: int = Field(gt=0)
    max_advance_days: int = Field(gt=0)
    payment_hold_minutes: int = Field(gt=0)
    approval_timeout_minutes: int = Field(gt=0)
    early_checkin_minutes: int = Field(ge=0)
    overstay_grace_minutes: int = Field(ge=0)
    overstay_block_minutes: int = Field(gt=0)
    overstay_block_fee: Decimal = Field(ge=0)
    free_cancellation_minutes: int = Field(ge=0)
    late_cancellation_fee_rate: Decimal = Field(ge=0, le=1)
    reminder_minutes_before_end: int = Field(gt=0)
    min_listing_photos: int = Field(ge=0)
    max_listing_photos: int = Field(gt=0)
    max_slots_per_listing: int = Field(gt=0)
    max_dispute_photos: int = Field(ge=0)
    search_default_radius_km: float = Field(gt=0)
    search_max_radius_km: float = Field(gt=0)
    search_max_results: int = Field(gt=0)
    default_page_size: int = Field(gt=0)
    max_page_size: int = Field(gt=0)

    def commission_for(self, listing_kind: str) -> Decimal:
        return self.commission_rate_commercial if listing_kind == "commercial" else self.commission_rate_private
