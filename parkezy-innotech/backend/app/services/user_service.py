import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import Conflict, Forbidden, NotFound
from app.db.models import Booking, Favorite, Listing, PushToken, SocialIdentity, User
from app.domain.enums import BLOCKING_STATUSES, ListingStatus, UserStatus
from app.infra.cache import Cache
from app.services.auth_service import AuthService
from app.services.listing_service import LISTINGS_CACHE_NS
from app.services.outbox import Event, Outbox


class UserService:
    def __init__(self, session: AsyncSession, clock: Clock, auth: AuthService, cache: Cache) -> None:
        self._session = session
        self._clock = clock
        self._auth = auth
        self._cache = cache
        self._outbox = Outbox(session, clock)

    async def update_profile(self, user: User, *, full_name: str | None, phone: str | None) -> User:
        if full_name is not None:
            user.full_name = full_name.strip()
        if phone is not None:
            user.phone = phone or None
        await self._session.commit()
        return user

    async def become_host(self, user: User) -> User:
        if user.email_verified_at is None:
            raise Forbidden("Verify your email before hosting", code="email_not_verified")
        if not user.phone:
            raise Forbidden("Add a phone number before hosting", code="phone_required")
        user.is_host = True
        await self._session.commit()
        return user

    async def grant_commercial_host(self, user_id: uuid.UUID) -> User:
        user = await self._session.get(User, user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            raise NotFound("User not found")
        user.is_host = True
        user.is_commercial_host = True
        await self._session.commit()
        return user

    async def register_push_token(self, user: User, token: str, platform: str) -> None:
        existing = (await self._session.execute(select(PushToken).where(PushToken.token == token))).scalar_one_or_none()
        now = self._clock.now()
        if existing:
            existing.user_id, existing.platform, existing.last_seen_at = user.id, platform, now
        else:
            self._session.add(PushToken(user_id=user.id, token=token, platform=platform, last_seen_at=now))
        await self._session.commit()

    async def remove_push_token(self, user: User, token: str) -> None:
        await self._session.execute(delete(PushToken).where(PushToken.user_id == user.id, PushToken.token == token))
        await self._session.commit()

    async def delete_account(self, user: User, password: str | None) -> None:
        """Anonymise personal data and close the account. Financial records (bookings,
        ledger) are kept for tax purposes but no longer identify the person."""
        if user.password_hash:
            await self._auth.confirm_password(user, password or "")
        live = list(BLOCKING_STATUSES)
        active = await self._session.scalar(
            select(func.count())
            .select_from(Booking)
            .where(
                (Booking.driver_id == user.id) | (Booking.host_id == user.id),
                Booking.status.in_(live),
            )
        )
        if active:
            raise Conflict(
                "Finish or cancel your active bookings before deleting your account",
                code="active_bookings",
                details={"active_bookings": active},
            )
        original_email, name = user.email, user.full_name
        now = self._clock.now()
        await self._session.execute(
            update(Listing)
            .where(Listing.owner_id == user.id, Listing.status != ListingStatus.ARCHIVED.value)
            .values(status=ListingStatus.ARCHIVED.value, updated_at=now)
        )
        await self._session.execute(delete(PushToken).where(PushToken.user_id == user.id))
        # Unlinking Google/Apple means signing in with them again starts a fresh account.
        await self._session.execute(delete(SocialIdentity).where(SocialIdentity.user_id == user.id))
        await self._session.execute(delete(Favorite).where(Favorite.user_id == user.id))
        await self._auth.revoke_all_sessions(user.id)
        user.email = f"deleted-{uuid.uuid4().hex}@deleted.invalid"
        user.full_name = "Deleted user"
        user.phone = None
        user.avatar_key = None
        user.password_hash = None
        user.status = UserStatus.DELETED.value
        user.is_host = user.is_commercial_host = user.is_admin = False
        user.deleted_at = now
        self._outbox.add(Event.ACCOUNT_DELETED, {"email": original_email, "full_name": name})
        await self._session.commit()
        await self._cache.bump(LISTINGS_CACHE_NS)
