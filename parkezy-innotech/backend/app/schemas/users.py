import re
import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.domain.enums import NotificationCategory, SocialProvider, UserStatus
from app.schemas.common import Schema

PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")


def _password(v: str) -> str:
    if not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
        raise ValueError("Password must contain letters and numbers")
    return v


def _phone(v: str | None) -> str | None:
    if v in (None, ""):
        return v
    cleaned = re.sub(r"[\s\-()]", "", v)
    if not PHONE_RE.match(cleaned):
        raise ValueError("Enter a valid phone number with country code, e.g. +919876543210")
    return cleaned


class RegisterRequest(Schema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = None

    _pw = field_validator("password")(_password)
    _ph = field_validator("phone")(_phone)


class LoginRequest(Schema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(Schema):
    refresh_token: str = Field(min_length=20, max_length=200)


class CodeRequest(Schema):
    code: str = Field(pattern=r"^\d{4,10}$")


class EmailRequest(Schema):
    email: EmailStr


class ResetPasswordRequest(Schema):
    email: EmailStr
    code: str = Field(pattern=r"^\d{4,10}$")
    new_password: str = Field(min_length=8, max_length=128)

    _pw = field_validator("new_password")(_password)


class ChangePasswordRequest(Schema):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    _pw = field_validator("new_password")(_password)


class ProfileUpdate(Schema):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None

    _ph = field_validator("phone")(_phone)


class PushTokenRequest(Schema):
    token: str = Field(min_length=10, max_length=255)
    platform: str = Field(pattern="^(ios|android)$")


class UserOut(Schema):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    email_verified: bool
    is_host: bool
    is_commercial_host: bool
    is_admin: bool
    created_at: datetime


class TokenOut(Schema):
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    token_type: str = "bearer"


class AuthOut(Schema):
    user: UserOut
    tokens: TokenOut


class NotificationPreferences(Schema):
    """channel -> category -> enabled, e.g. {"email": {"receipts": false}}."""

    push: dict[NotificationCategory, bool] = {}
    email: dict[NotificationCategory, bool] = {}


class DeleteAccountRequest(Schema):
    # Required when the account has a password; Google/Apple-only accounts have none to confirm.
    password: str | None = Field(default=None, min_length=1, max_length=128)


class SocialSignInRequest(Schema):
    provider: SocialProvider
    id_token: str = Field(min_length=1, max_length=8192)
    nonce: str | None = Field(default=None, max_length=256)
    # Apple only shares the name on the very first sign-in, and only with the app.
    full_name: str | None = Field(default=None, max_length=120)


class AdminUserOut(UserOut):
    status: UserStatus


class AdminUserDetail(AdminUserOut):
    listings_count: int
    bookings_count: int
    suspension_reason: str | None
    suspended_at: datetime | None


class SuspendRequest(Schema):
    reason: str = Field(min_length=3, max_length=500)
