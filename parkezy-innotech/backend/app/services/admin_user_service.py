"""Admin user management: search, inspect, suspend and reinstate accounts."""

import uuid

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import Conflict, NotFound
from app.db.models import Booking, Listing, User
from app.domain.enums import ListingStatus, UserStatus
from app.infra.cache import Cache
from app.services.auth_service import AuthService
from app.services.listing_service import LISTINGS_CACHE_NS
from app.services.pagination import decode_cursor, page


def _like_literal(text: str) -> str:
    """Escape LIKE wildcards so a search for '%' finds a literal percent sign."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AdminUserService:
    def __init__(self, session: AsyncSession, clock: Clock, auth: AuthService, cache: Cache) -> None:
        self._session = session
        self._clock = clock
        self._auth = auth
        self._cache = cache

    async def search(
        self, *, q: str | None, status: UserStatus | None, cursor: str | None, limit: int
    ) -> tuple[list[User], str | None]:
        query = select(User)
        if q and q.strip():
            pattern = f"%{_like_literal(q.strip())}%"
            query = query.where(or_(User.email.ilike(pattern, escape="\\"), User.full_name.ilike(pattern, escape="\\")))
        if status:
            query = query.where(User.status == status.value)
        if cursor:
            created, uid = decode_cursor(cursor)
            query = query.where(tuple_(User.created_at, User.id) < tuple_(created, uid))
        rows = list(
            (await self._session.execute(query.order_by(User.created_at.desc(), User.id.desc()).limit(limit + 1)))
            .scalars()
            .all()
        )
        return page(rows, limit, key=lambda u: (u.created_at, u.id))

    async def get(self, user_id: uuid.UUID, *, lock: bool = False) -> User:
        query = select(User).where(User.id == user_id)
        if lock:
            query = query.with_for_update()
        user = (await self._session.execute(query)).scalar_one_or_none()
        if user is None:
            raise NotFound("User not found")
        return user

    async def counts(self, user: User) -> dict[str, int]:
        listings = await self._session.scalar(
            select(func.count()).where(Listing.owner_id == user.id, Listing.status != ListingStatus.ARCHIVED.value)
        )
        bookings = await self._session.scalar(select(func.count()).where(Booking.driver_id == user.id))
        return {"listings_count": int(listings or 0), "bookings_count": int(bookings or 0)}

    async def suspend(self, admin: User, user_id: uuid.UUID, reason: str) -> User:
        user = await self.get(user_id, lock=True)
        if user.id == admin.id:
            raise Conflict("You can't suspend your own account", code="cannot_suspend_self")
        if user.status == UserStatus.DELETED.value:
            raise Conflict("This account was deleted", code="user_deleted")
        if user.is_admin:
            raise Conflict("Admins can't be suspended here; remove admin rights first", code="cannot_suspend_admin")
        if user.status == UserStatus.SUSPENDED.value:
            raise Conflict("This account is already suspended", code="already_suspended")
        user.status = UserStatus.SUSPENDED.value
        user.suspended_at = self._clock.now()
        user.suspension_reason = reason
        await self._auth.revoke_all_sessions(user.id)  # signs them out everywhere, right now
        await self._session.commit()
        await self._cache.bump(LISTINGS_CACHE_NS)  # their spots leave search immediately
        return user

    async def unsuspend(self, user_id: uuid.UUID) -> User:
        user = await self.get(user_id, lock=True)
        if user.status != UserStatus.SUSPENDED.value:
            raise Conflict("This account is not suspended", code="not_suspended")
        user.status = UserStatus.ACTIVE.value
        user.suspended_at = None
        user.suspension_reason = None
        await self._session.commit()
        await self._cache.bump(LISTINGS_CACHE_NS)
        return user
