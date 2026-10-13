"""Parking access credentials.

PIN: derived as HMAC(secret, booking_id) so nothing secret is stored in the database and the
driver can always re-display it. Rotating ACCESS_CODE_SECRET invalidates every PIN.
QR: a short-lived signed token (see TokenService) carrying the booking id and a one-time jti.
"""

import uuid

from app.core.security import constant_time_equals, hmac_hex


class AccessCodeService:
    def __init__(self, secret: str, pin_length: int) -> None:
        self._secret = secret
        self._pin_length = pin_length

    def pin_for(self, booking_id: uuid.UUID) -> str:
        digest = int(hmac_hex(self._secret, f"pin:{booking_id}"), 16)
        return str(digest % 10**self._pin_length).zfill(self._pin_length)

    def verify_pin(self, booking_id: uuid.UUID, pin: str) -> bool:
        return constant_time_equals(self.pin_for(booking_id), pin)
