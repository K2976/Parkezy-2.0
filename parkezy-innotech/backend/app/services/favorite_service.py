"""Saved ("favourite") spots. Hidden, not deleted, while a listing is paused or its host is
suspended, so they come back on their own when the listing does."""

import uuid

from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import NotFound
from app.db.models import Favorite, Listing, ListingMedia, User
from app.services.listing_service import bookable_clause
from app.services.pagination import decode_cursor, page


class FavoriteService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def save(self, user: User, listing_id: uuid.UUID) -> None:
        bookable = await self._session.scalar(select(Listing.id).where(Listing.id == listing_id, bookable_clause()))
        if bookable is None:
            raise NotFound("Listing not found")
        await self._session.execute(
            insert(Favorite)
            .values(user_id=user.id, listing_id=listing_id, created_at=self._clock.now())
            .on_conflict_do_nothing(index_elements=["user_id", "listing_id"])
        )
        await self._session.commit()

    async def remove(self, user: User, listing_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id)
        )
        await self._session.commit()

    async def is_saved(self, user: User | None, listing_id: uuid.UUID) -> bool:
        if user is None:
            return False
        found = await self._session.scalar(
            select(Favorite.listing_id).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id)
        )
        return found is not None

    async def list(
        self, user: User, *, cursor: str | None, limit: int
    ) -> tuple[list[tuple[Listing, Favorite, str | None]], str | None]:
        cover = (
            select(ListingMedia.storage_key)
            .where(ListingMedia.listing_id == Listing.id)
            .order_by(ListingMedia.position)
            .limit(1)
            .scalar_subquery()
        )
        query = (
            select(Listing, Favorite, cover.label("cover_key"))
            .join(Favorite, Favorite.listing_id == Listing.id)
            .where(Favorite.user_id == user.id, bookable_clause())
        )
        if cursor:
            saved_at, listing_id = decode_cursor(cursor)
            query = query.where(tuple_(Favorite.created_at, Favorite.listing_id) < tuple_(saved_at, listing_id))
        rows = (
            await self._session.execute(
                query.order_by(Favorite.created_at.desc(), Favorite.listing_id.desc()).limit(limit + 1)
            )
        ).all()
        items = [(r[0], r[1], r.cover_key) for r in rows]
        return page(items, limit, key=lambda item: (item[1].created_at, item[1].listing_id))
