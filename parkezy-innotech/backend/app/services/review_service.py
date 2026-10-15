"""Reviews: one per completed booking, written by its driver inside the review window.

listings.rating_avg / rating_count are a denormalised summary, recomputed from the reviews
table on every change while holding the listing's row lock, so concurrent reviews of the same
listing can never leave a stale average."""

import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import Conflict, NotFound
from app.db.models import Booking, Listing, Review, User
from app.domain.enums import BookingStatus
from app.domain.rules import PlatformRules
from app.infra.cache import Cache
from app.services.listing_service import LISTINGS_CACHE_NS, bookable_clause
from app.services.pagination import decode_cursor, page


class ReviewService:
    def __init__(self, session: AsyncSession, clock: Clock, cache: Cache) -> None:
        self._session = session
        self._clock = clock
        self._cache = cache

    # ------------------------------------------------------------ helpers
    def _ensure_window_open(self, booking: Booking, rules: PlatformRules) -> None:
        closes = (booking.checked_out_at or booking.ends_at) + timedelta(days=rules.review_window_days)
        if self._clock.now() > closes:
            raise Conflict(
                f"Reviews can be written up to {rules.review_window_days} days after your visit",
                code="review_window_closed",
            )

    async def _lock_listing(self, listing_id: uuid.UUID) -> None:
        await self._session.execute(select(Listing.id).where(Listing.id == listing_id).with_for_update())

    async def _recompute(self, listing_id: uuid.UUID) -> None:
        """Caller holds the listing row lock (taken before this statement's snapshot)."""
        avg, count = (
            await self._session.execute(
                select(func.avg(Review.rating), func.count()).where(Review.listing_id == listing_id)
            )
        ).one()
        listing = await self._session.get(Listing, listing_id)
        assert listing is not None
        listing.rating_count = int(count)
        listing.rating_avg = None if not count else Decimal(avg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def _commit(self) -> None:
        await self._session.commit()
        await self._cache.bump(LISTINGS_CACHE_NS)  # ratings are part of cached search results

    async def _own_review(self, author: User, review_id: uuid.UUID) -> Review:
        review = await self._session.get(Review, review_id)
        if review is None or review.author_id != author.id:
            raise NotFound("Review not found")
        return review

    # ------------------------------------------------------------ driver
    async def create(
        self, driver: User, booking_id: uuid.UUID, *, rating: int, comment: str | None, rules: PlatformRules
    ) -> Review:
        booking = (
            await self._session.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
        ).scalar_one_or_none()
        if booking is None or booking.driver_id != driver.id:
            raise NotFound("Booking not found")
        if booking.status != BookingStatus.COMPLETED.value:
            raise Conflict("You can review a spot after you've parked there", code="not_reviewable")
        self._ensure_window_open(booking, rules)
        exists = await self._session.scalar(select(Review.id).where(Review.booking_id == booking.id))
        if exists:
            raise Conflict("You've already reviewed this booking", code="already_reviewed")
        await self._lock_listing(booking.listing_id)
        review = Review(
            booking_id=booking.id, listing_id=booking.listing_id, author_id=driver.id, rating=rating, comment=comment
        )
        self._session.add(review)
        try:
            await self._session.flush()
        except IntegrityError as e:  # belt and braces: the booking lock already serialises this
            await self._session.rollback()
            raise Conflict("You've already reviewed this booking", code="already_reviewed") from e
        await self._recompute(booking.listing_id)
        await self._commit()
        return review

    async def update(
        self,
        author: User,
        review_id: uuid.UUID,
        *,
        rating: int | None,
        comment: str | None,
        clear_comment: bool,
        rules: PlatformRules,
    ) -> Review:
        review = await self._own_review(author, review_id)
        booking = await self._session.get(Booking, review.booking_id)
        assert booking is not None
        self._ensure_window_open(booking, rules)
        await self._lock_listing(review.listing_id)
        if rating is not None:
            review.rating = rating
        if comment is not None or clear_comment:
            review.comment = comment
        await self._session.flush()
        await self._recompute(review.listing_id)
        await self._commit()
        await self._session.refresh(review)
        return review

    async def delete(self, author: User, review_id: uuid.UUID) -> None:
        review = await self._own_review(author, review_id)
        await self._lock_listing(review.listing_id)
        await self._session.delete(review)
        await self._session.flush()
        await self._recompute(review.listing_id)
        await self._commit()

    # ------------------------------------------------------------ host
    async def reply(self, host: User, review_id: uuid.UUID, text: str) -> Review:
        review = (
            await self._session.execute(select(Review).where(Review.id == review_id).with_for_update())
        ).scalar_one_or_none()
        owner = (
            None
            if review is None
            else await self._session.scalar(select(Listing.owner_id).where(Listing.id == review.listing_id))
        )
        if review is None or owner != host.id:
            raise NotFound("Review not found")
        if review.host_reply is not None:
            raise Conflict("You've already replied to this review", code="already_replied")
        review.host_reply = text
        review.host_replied_at = self._clock.now()
        await self._session.commit()
        await self._session.refresh(review)
        return review

    # ------------------------------------------------------------ public
    async def list_for_listing(
        self, listing_id: uuid.UUID, *, cursor: str | None, limit: int
    ) -> tuple[list[Review], str | None]:
        visible = await self._session.scalar(select(Listing.id).where(Listing.id == listing_id, bookable_clause()))
        if visible is None:
            raise NotFound("Listing not found")
        query = select(Review).where(Review.listing_id == listing_id)
        if cursor:
            created, rid = decode_cursor(cursor)
            query = query.where(tuple_(Review.created_at, Review.id) < tuple_(created, rid))
        rows = list(
            (await self._session.execute(query.order_by(Review.created_at.desc(), Review.id.desc()).limit(limit + 1)))
            .scalars()
            .all()
        )
        return page(rows, limit, key=lambda r: (r.created_at, r.id))

    async def authors(self, reviews: list[Review]) -> dict[uuid.UUID, User]:
        ids = {r.author_id for r in reviews}
        if not ids:
            return {}
        return {u.id: u for u in (await self._session.execute(select(User).where(User.id.in_(ids)))).scalars()}
