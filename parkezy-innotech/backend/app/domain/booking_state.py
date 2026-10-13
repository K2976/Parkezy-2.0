"""Booking lifecycle. The only place that decides which status changes are legal.

request (needs approval) ─► pending_approval ─approve─► pending_payment* ─pay─► confirmed
request (auto-accept)    ─────────────────────────────► pending_payment* ─pay─► confirmed
confirmed ─check-in─► checked_in ─check-out─► completed
* skipped when payment mode is pay_at_venue (goes straight to confirmed)
"""

from app.core.errors import Conflict
from app.domain.enums import BookingStatus as S

TRANSITIONS: dict[S, frozenset[S]] = {
    S.PENDING_APPROVAL: frozenset({S.PENDING_PAYMENT, S.CONFIRMED, S.REJECTED, S.CANCELLED, S.EXPIRED}),
    S.PENDING_PAYMENT: frozenset({S.CONFIRMED, S.CANCELLED, S.EXPIRED}),
    S.CONFIRMED: frozenset({S.CHECKED_IN, S.CANCELLED, S.EXPIRED}),
    S.CHECKED_IN: frozenset({S.COMPLETED}),
    S.COMPLETED: frozenset(),
    S.CANCELLED: frozenset(),
    S.REJECTED: frozenset(),
    S.EXPIRED: frozenset(),
}


def can_transition(current: S | str, target: S) -> bool:
    return target in TRANSITIONS[S(current)]


def ensure_transition(current: S | str, target: S) -> None:
    if not can_transition(current, target):
        raise Conflict(
            f"Booking cannot move from {S(current).value} to {target.value}",
            code="invalid_booking_transition",
            details={"from": S(current).value, "to": target.value},
        )


def status_after_request(*, auto_accept: bool, online_payment: bool) -> S:
    if not auto_accept:
        return S.PENDING_APPROVAL
    return S.PENDING_PAYMENT if online_payment else S.CONFIRMED


def status_after_approval(*, online_payment: bool) -> S:
    return S.PENDING_PAYMENT if online_payment else S.CONFIRMED
