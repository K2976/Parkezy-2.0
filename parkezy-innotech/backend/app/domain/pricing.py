"""Price calculation. Pure functions, Decimal only, rounded half-up to paise."""

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
MINUTES_PER_DAY = 24 * 60


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PriceBreakdown:
    hourly_rate: Decimal
    duration_minutes: int
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    commission_rate: Decimal
    platform_fee: Decimal
    host_earnings: Decimal
    currency: str


def _chunk_cost(minutes: int, hourly_rate: Decimal, daily_cap: Decimal | None) -> Decimal:
    cost = hourly_rate * Decimal(minutes) / Decimal(60)
    return min(cost, daily_cap) if daily_cap is not None else cost


def quote(
    *,
    starts_at: datetime,
    ends_at: datetime,
    hourly_rate: Decimal,
    daily_cap: Decimal | None,
    tax_rate: Decimal,
    commission_rate: Decimal,
    currency: str,
) -> PriceBreakdown:
    """Pro-rata by minute; each started 24h block is capped at `daily_cap` if set."""
    minutes = int((ends_at - starts_at).total_seconds() // 60)
    if minutes <= 0:
        raise ValueError("ends_at must be after starts_at")
    full_days, remainder = divmod(minutes, MINUTES_PER_DAY)
    raw = _chunk_cost(MINUTES_PER_DAY, hourly_rate, daily_cap) * full_days
    if remainder:
        raw += _chunk_cost(remainder, hourly_rate, daily_cap)
    subtotal = money(raw)
    tax = money(subtotal * tax_rate)
    fee = money(subtotal * commission_rate)
    return PriceBreakdown(
        hourly_rate=hourly_rate,
        duration_minutes=minutes,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax,
        total=subtotal + tax,
        commission_rate=commission_rate,
        platform_fee=fee,
        host_earnings=subtotal - fee,
        currency=currency,
    )


@dataclass(frozen=True)
class OverstayCharge:
    minutes: int
    fee: Decimal
    tax: Decimal


def overstay(
    *,
    ends_at: datetime,
    checked_out_at: datetime,
    grace_minutes: int,
    block_minutes: int,
    block_fee: Decimal,
    tax_rate: Decimal,
) -> OverstayCharge:
    """Fee per *started* block after the grace period; minutes counted from the booked end."""
    over_seconds = (checked_out_at - ends_at).total_seconds()
    minutes = max(0, math.ceil(over_seconds / 60))
    if minutes <= grace_minutes:
        return OverstayCharge(minutes=minutes, fee=Decimal("0.00"), tax=Decimal("0.00"))
    blocks = math.ceil(minutes / block_minutes)
    fee = money(block_fee * blocks)
    return OverstayCharge(minutes=minutes, fee=fee, tax=money(fee * tax_rate))


def cancellation_fee(
    *, subtotal: Decimal, minutes_before_start: float, free_minutes: int, fee_rate: Decimal
) -> Decimal:
    if minutes_before_start >= free_minutes:
        return Decimal("0.00")
    return money(subtotal * fee_rate)
