"""Registration, login, refresh-token rotation, email verification and password reset.

Refresh tokens are opaque, stored hashed, rotated on every use, and grouped in families:
re-using an already-rotated token revokes the whole family (stolen-token detection).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import Conflict, Forbidden, Unauthorized, ValidationFailed
from app.core.security import (
    PasswordHasher,
    TokenService,
    new_opaque_token,
    random_digits,
    sha256_hex,
)
from app.db.models import RefreshToken, User, VerificationCode
from app.domain.enums import CodePurpose, UserStatus
from app.services.outbox import Event, Outbox

ACCESS_PURPOSE = "access"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock,
    ) -> None:
        self._session = session
        self._settings = settings
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock
        self._outbox = Outbox(session, clock)

    # ---------------------------------------------------------------- tokens
    def _access_token(self, user: User, now: datetime) -> tuple[str, datetime]:
        ttl = timedelta(minutes=self._settings.access_token_ttl_minutes)
        return self._tokens.encode(str(user.id), ACCESS_PURPOSE, now, ttl), now + ttl

    def _new_refresh(self, user_id: uuid.UUID, family_id: uuid.UUID, now: datetime, ua: str | None):
        raw = new_opaque_token()
        expires = now + timedelta(days=self._settings.refresh_token_ttl_days)
        self._session.add(
            RefreshToken(
                user_id=user_id,
                token_hash=sha256_hex(raw),
                family_id=family_id,
                expires_at=expires,
                user_agent=(ua or "")[:255] or None,
                created_at=now,
            )
        )
        return raw, expires

    async def _issue(self, user: User, ua: str | None, family_id: uuid.UUID | None = None) -> TokenPair:
        now = self._clock.now()
        access, access_exp = self._access_token(user, now)
        refresh, refresh_exp = self._new_refresh(user.id, family_id or uuid.uuid4(), now, ua)
        await self._session.commit()
        return TokenPair(access, access_exp, refresh, refresh_exp)

    def user_id_from_access_token(self, token: str) -> uuid.UUID:
        payload = self._tokens.decode(token, ACCESS_PURPOSE)
        return uuid.UUID(payload["sub"])

    # ---------------------------------------------------------------- codes
    def _issue_code(self, user: User, purpose: CodePurpose) -> None:
        now = self._clock.now()
        code = random_digits(self._settings.verification_code_length)
        self._session.add(
            VerificationCode(
                user_id=user.id,
                purpose=purpose.value,
                code_hash=sha256_hex(f"{user.id}:{purpose}:{code}"),
                expires_at=now + timedelta(minutes=self._settings.verification_code_ttl_minutes),
                attempts=0,
                created_at=now,
            )
        )
        self._outbox.add(
            Event.VERIFICATION_CODE,
            {
                "user_id": str(user.id),
                "purpose": purpose.value,
                "code": code,
                "ttl_minutes": self._settings.verification_code_ttl_minutes,
            },
        )

    async def _consume_code(self, user: User, purpose: CodePurpose, code: str) -> None:
        now = self._clock.now()
        record = (
            await self._session.execute(
                select(VerificationCode)
                .where(
                    VerificationCode.user_id == user.id,
                    VerificationCode.purpose == purpose.value,
                    VerificationCode.consumed_at.is_(None),
                )
                .order_by(VerificationCode.created_at.desc(), VerificationCode.id.desc())
                .limit(1)
                .with_for_update()
            )
        ).scalar_one_or_none()
        invalid = ValidationFailed("Invalid or expired code", code="invalid_code")
        if record is None or record.expires_at <= now:
            raise invalid
        if record.attempts >= self._settings.verification_code_max_attempts:
            raise ValidationFailed("Too many attempts, request a new code", code="code_locked")
        if record.code_hash != sha256_hex(f"{user.id}:{purpose}:{code}"):
            record.attempts += 1
            await self._session.commit()
            raise invalid
        record.consumed_at = now

    # ---------------------------------------------------------------- flows
    async def register(self, *, email: str, password: str, full_name: str, phone: str | None) -> User:
        user = User(
            email=email.lower(),
            password_hash=self._hasher.hash(password),
            full_name=full_name.strip(),
            phone=phone,
            status=UserStatus.ACTIVE.value,
            is_host=False,
            is_commercial_host=False,
            is_admin=email.lower() in self._settings.admin_emails,
        )
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError as e:
            await self._session.rollback()
            raise Conflict("An account with this email already exists", code="email_taken") from e
        self._issue_code(user, CodePurpose.EMAIL_VERIFY)
        await self._session.commit()
        return user

    async def _active_user_by_email(self, email: str) -> User | None:
        return (
            await self._session.execute(
                select(User).where(User.email == email.lower(), User.status == UserStatus.ACTIVE.value)
            )
        ).scalar_one_or_none()

    async def login(self, *, email: str, password: str, user_agent: str | None) -> tuple[User, TokenPair]:
        user = await self._active_user_by_email(email)
        if user is None or not user.password_hash or not self._hasher.verify(user.password_hash, password):
            raise Unauthorized("Incorrect email or password", code="invalid_credentials")
        if self._hasher.needs_rehash(user.password_hash):
            user.password_hash = self._hasher.hash(password)
        return user, await self._issue(user, user_agent)

    async def issue_for(self, user: User, user_agent: str | None) -> TokenPair:
        return await self._issue(user, user_agent)

    async def refresh(self, *, refresh_token: str, user_agent: str | None) -> TokenPair:
        now = self._clock.now()
        record = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(refresh_token)).with_for_update()
            )
        ).scalar_one_or_none()
        if record is None or record.expires_at <= now:
            raise Unauthorized("Session expired, please sign in again", code="refresh_invalid")
        if record.revoked_at is not None:
            # A rotated token was replayed: assume theft and end every session in the family.
            await self._revoke_family(record.family_id, now)
            await self._session.commit()
            raise Unauthorized("Session expired, please sign in again", code="refresh_reused")
        user = await self._session.get(User, record.user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            raise Unauthorized("Account unavailable", code="account_inactive")
        record.revoked_at = now
        return await self._issue(user, user_agent, family_id=record.family_id)

    async def _revoke_family(self, family_id: uuid.UUID, now: datetime) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def logout(self, *, refresh_token: str) -> None:
        record = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(refresh_token))
            )
        ).scalar_one_or_none()
        if record is not None:
            await self._revoke_family(record.family_id, self._clock.now())
            await self._session.commit()

    async def revoke_all_sessions(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=self._clock.now())
        )

    async def verify_email(self, user: User, code: str) -> User:
        if user.email_verified_at is not None:
            return user
        await self._consume_code(user, CodePurpose.EMAIL_VERIFY, code)
        user.email_verified_at = self._clock.now()
        await self._session.commit()
        return user

    async def resend_verification(self, user: User) -> None:
        if user.email_verified_at is not None:
            raise Conflict("Email is already verified", code="already_verified")
        self._issue_code(user, CodePurpose.EMAIL_VERIFY)
        await self._session.commit()

    async def forgot_password(self, email: str) -> None:
        """Always succeeds from the caller's view so accounts cannot be enumerated."""
        user = await self._active_user_by_email(email)
        if user is None:
            return
        self._issue_code(user, CodePurpose.PASSWORD_RESET)
        await self._session.commit()

    async def reset_password(self, *, email: str, code: str, new_password: str) -> None:
        user = await self._active_user_by_email(email)
        if user is None:
            raise ValidationFailed("Invalid or expired code", code="invalid_code")
        await self._consume_code(user, CodePurpose.PASSWORD_RESET, code)
        user.password_hash = self._hasher.hash(new_password)
        # A successful reset proves inbox ownership.
        user.email_verified_at = user.email_verified_at or self._clock.now()
        await self.revoke_all_sessions(user.id)
        self._outbox.add(Event.PASSWORD_CHANGED, {"user_id": str(user.id)})
        await self._session.commit()

    def confirm_password(self, user: User, password: str) -> None:
        """Re-authentication for sensitive actions: a stolen unlocked phone is not enough."""
        if not user.password_hash or not self._hasher.verify(user.password_hash, password):
            raise Forbidden("Current password is incorrect", code="invalid_credentials")

    async def change_password(self, user: User, *, current_password: str, new_password: str) -> None:
        self.confirm_password(user, current_password)
        user.password_hash = self._hasher.hash(new_password)
        await self.revoke_all_sessions(user.id)
        self._outbox.add(Event.PASSWORD_CHANGED, {"user_id": str(user.id)})
        await self._session.commit()
