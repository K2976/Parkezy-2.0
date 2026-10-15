"""Pure domain logic: pricing, state machine, opening hours, access codes, signatures."""

import base64
import hashlib
import hmac
import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.core.errors import Conflict, ValidationFailed
from app.domain import booking_state
from app.domain.access import AccessCodeService
from app.domain.availability import OpeningHours, is_within_hours, validate_window
from app.domain.enums import BookingStatus as S
from app.domain.pricing import cancellation_fee, overstay, quote
from app.domain.rules import PlatformRules
from app.integrations.webhooks import verify_svix_signature

RULES = PlatformRules(
    currency="INR",
    gst_rate=Decimal("0.18"),
    commission_rate_private=Decimal("0.15"),
    commission_rate_commercial=Decimal("0.12"),
    booking_step_minutes=15,
    min_booking_minutes=30,
    max_booking_minutes=10080,
    max_advance_days=30,
    payment_hold_minutes=10,
    approval_timeout_minutes=30,
    early_checkin_minutes=15,
    overstay_grace_minutes=5,
    overstay_block_minutes=15,
    overstay_block_fee=Decimal("20"),
    free_cancellation_minutes=60,
    late_cancellation_fee_rate=Decimal("0.25"),
    reminder_minutes_before_end=15,
    min_listing_photos=1,
    max_listing_photos=5,
    max_slots_per_listing=500,
    max_dispute_photos=5,
    search_default_radius_km=5,
    search_max_radius_km=25,
    search_max_results=200,
    default_page_size=20,
    max_page_size=100,
    review_window_days=14,
    min_payout_amount=Decimal("100.00"),
)
T0 = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)


def test_quote_basic_with_gst_and_commission():
    p = quote(
        starts_at=T0,
        ends_at=T0 + timedelta(hours=2, minutes=30),
        hourly_rate=Decimal("40"),
        daily_cap=None,
        tax_rate=Decimal("0.18"),
        commission_rate=Decimal("0.15"),
        currency="INR",
    )
    assert p.subtotal == Decimal("100.00")
    assert p.tax_amount == Decimal("18.00")
    assert p.total == Decimal("118.00")
    assert p.platform_fee == Decimal("15.00")
    assert p.host_earnings == Decimal("85.00")


def test_quote_daily_cap_applies_per_24h_block():
    p = quote(
        starts_at=T0,
        ends_at=T0 + timedelta(hours=30),
        hourly_rate=Decimal("40"),
        daily_cap=Decimal("300"),
        tax_rate=Decimal("0.18"),
        commission_rate=Decimal("0"),
        currency="INR",
    )
    # 24h capped at 300 + 6h at 40/h = 240
    assert p.subtotal == Decimal("540.00")


def test_quote_rounds_half_up_to_paise():
    p = quote(
        starts_at=T0,
        ends_at=T0 + timedelta(minutes=45),
        hourly_rate=Decimal("33.33"),
        daily_cap=None,
        tax_rate=Decimal("0.18"),
        commission_rate=Decimal("0.15"),
        currency="INR",
    )
    assert p.subtotal == Decimal("25.00")  # 24.9975 -> 25.00
    assert p.tax_amount == Decimal("4.50")


@pytest.mark.parametrize(
    ("over_minutes", "fee"),
    [(0, "0"), (5, "0"), (6, "20"), (15, "20"), (16, "40"), (61, "100")],
)
def test_overstay_per_started_block_after_grace(over_minutes, fee):
    c = overstay(
        ends_at=T0,
        checked_out_at=T0 + timedelta(minutes=over_minutes),
        grace_minutes=5,
        block_minutes=15,
        block_fee=Decimal("20"),
        tax_rate=Decimal("0.18"),
    )
    assert c.fee == Decimal(fee)
    assert c.tax == (Decimal(fee) * Decimal("0.18")).quantize(Decimal("0.01"))


def test_cancellation_fee_only_inside_window():
    assert (
        cancellation_fee(subtotal=Decimal("100"), minutes_before_start=120, free_minutes=60, fee_rate=Decimal("0.25"))
        == 0
    )
    assert cancellation_fee(
        subtotal=Decimal("100"), minutes_before_start=30, free_minutes=60, fee_rate=Decimal("0.25")
    ) == Decimal("25.00")


def test_state_machine_rejects_illegal_transitions():
    assert booking_state.can_transition(S.CONFIRMED, S.CHECKED_IN)
    assert not booking_state.can_transition(S.COMPLETED, S.CANCELLED)
    with pytest.raises(Conflict):
        booking_state.ensure_transition(S.CHECKED_IN, S.CANCELLED)
    for terminal in (S.COMPLETED, S.CANCELLED, S.REJECTED, S.EXPIRED):
        assert booking_state.TRANSITIONS[terminal] == frozenset()


@pytest.mark.parametrize(
    ("auto", "online", "expected"),
    [
        (True, True, S.PENDING_PAYMENT),
        (True, False, S.CONFIRMED),
        (False, True, S.PENDING_APPROVAL),
        (False, False, S.PENDING_APPROVAL),
    ],
)
def test_initial_status(auto, online, expected):
    assert booking_state.status_after_request(auto_accept=auto, online_payment=online) == expected


def test_validate_window_rules():
    now = T0
    validate_window(T0 + timedelta(hours=1), T0 + timedelta(hours=2), now, RULES)
    with pytest.raises(ValidationFailed, match="boundary"):
        validate_window(T0 + timedelta(minutes=7), T0 + timedelta(hours=2), now, RULES)
    with pytest.raises(ValidationFailed, match="duration"):
        validate_window(T0 + timedelta(hours=1), T0 + timedelta(hours=1, minutes=15), now, RULES)
    with pytest.raises(ValidationFailed, match="past"):
        validate_window(T0 - timedelta(hours=1), T0 + timedelta(hours=1), now, RULES)
    with pytest.raises(ValidationFailed, match="far"):
        validate_window(T0 + timedelta(days=31), T0 + timedelta(days=31, hours=1), now, RULES)
    # "park now": the current 15-minute block is still bookable
    validate_window(T0, T0 + timedelta(hours=1), now + timedelta(minutes=10), RULES)


def test_opening_hours_in_listing_timezone():
    hours = OpeningHours("Asia/Kolkata", False, time(9, 0), time(21, 0), (1, 2, 3, 4, 5))
    # Wed 14 Oct 2026 10:00 IST = 04:30 UTC
    start = datetime(2026, 10, 14, 4, 30, tzinfo=UTC)
    assert is_within_hours(start, start + timedelta(hours=2), hours)
    assert not is_within_hours(start, start + timedelta(hours=12), hours)  # past 21:00
    sat = start + timedelta(days=3)
    assert not is_within_hours(sat, sat + timedelta(hours=1), hours)
    all_day = OpeningHours("Asia/Kolkata", True, None, None, (1, 2, 3, 4, 5, 6, 7))
    assert is_within_hours(start, start + timedelta(days=2), all_day)


def test_pin_is_stable_secret_dependent_and_verifiable():
    a = AccessCodeService("secret-a", 6)
    booking = uuid.uuid4()
    pin = a.pin_for(booking)
    assert len(pin) == 6 and pin.isdigit()
    assert a.pin_for(booking) == pin
    assert a.verify_pin(booking, pin)
    assert not a.verify_pin(booking, str((int(pin) + 1) % 10**6).zfill(6))
    # Different secrets give unrelated PINs (equal only by 1-in-a-million chance).
    assert len({AccessCodeService(f"s{i}", 6).pin_for(booking) for i in range(20)}) > 15


def test_svix_signature_verification():
    secret = "whsec_" + base64.b64encode(b"super-secret-key").decode()
    body = b'{"type":"email.delivered"}'
    now = datetime.now(UTC)
    ts = str(int(now.timestamp()))
    sig = base64.b64encode(hmac.new(b"super-secret-key", f"m1.{ts}.".encode() + body, hashlib.sha256).digest())
    header = f"v1,bogus v1,{sig.decode()}"
    assert verify_svix_signature(secret=secret, msg_id="m1", timestamp=ts, signature_header=header, body=body, now=now)
    assert not verify_svix_signature(
        secret=secret, msg_id="m2", timestamp=ts, signature_header=header, body=body, now=now
    )
    old = now + timedelta(minutes=10)
    assert not verify_svix_signature(
        secret=secret, msg_id="m1", timestamp=ts, signature_header=header, body=body, now=old
    )
