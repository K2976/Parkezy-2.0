"""Validation of a requested parking window against platform rules and listing hours."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.errors import ValidationFailed
from app.domain.rules import PlatformRules


@dataclass(frozen=True)
class OpeningHours:
    timezone: str
    is_24h: bool
    open_time: time | None
    close_time: time | None
    open_days: tuple[int, ...]  # ISO weekdays, 1 = Monday


def validate_window(starts_at: datetime, ends_at: datetime, now: datetime, rules: PlatformRules) -> None:
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        raise ValidationFailed("Times must include a timezone offset", code="naive_datetime")
    step = rules.booking_step_minutes
    for label, value in (("starts_at", starts_at), ("ends_at", ends_at)):
        if value.second or value.microsecond or value.minute % step:
            raise ValidationFailed(
                f"{label} must be on a {step}-minute boundary",
                code="time_not_aligned",
                details={"field": label, "step_minutes": step},
            )
    minutes = (ends_at - starts_at).total_seconds() / 60
    if minutes < rules.min_booking_minutes or minutes > rules.max_booking_minutes:
        raise ValidationFailed(
            "Booking duration is out of range",
            code="duration_out_of_range",
            details={"min_minutes": rules.min_booking_minutes, "max_minutes": rules.max_booking_minutes},
        )
    # The current step block is still bookable ("park now").
    if starts_at < now - timedelta(minutes=step):
        raise ValidationFailed("Start time is in the past", code="start_in_past")
    if starts_at > now + timedelta(days=rules.max_advance_days):
        raise ValidationFailed(
            "Start time is too far ahead",
            code="start_too_far",
            details={"max_advance_days": rules.max_advance_days},
        )


def _days_touched(start_local: datetime, end_local: datetime) -> list[date]:
    last = (end_local - timedelta(microseconds=1)).date()
    days, current = [], start_local.date()
    while current <= last:
        days.append(current)
        current += timedelta(days=1)
    return days


def is_within_hours(starts_at: datetime, ends_at: datetime, hours: OpeningHours) -> bool:
    tz = ZoneInfo(hours.timezone)
    start_local, end_local = starts_at.astimezone(tz), ends_at.astimezone(tz)
    days = _days_touched(start_local, end_local)
    if any(d.isoweekday() not in hours.open_days for d in days):
        return False
    if hours.is_24h:
        return True
    if len(days) != 1 or hours.open_time is None or hours.close_time is None:
        return False
    end_time = end_local.time()
    if end_local.date() != start_local.date():  # ends exactly at midnight
        end_time = time(23, 59, 59, 999999)
    return hours.open_time <= start_local.time() and end_time <= hours.close_time


def ensure_within_hours(starts_at: datetime, ends_at: datetime, hours: OpeningHours) -> None:
    if not is_within_hours(starts_at, ends_at, hours):
        raise ValidationFailed("The listing is closed during part of this window", code="outside_hours")
