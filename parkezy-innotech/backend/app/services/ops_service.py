"""Operational views for admins: the outbox dead-letter queue (System Design Interview ch. 26/19).

Events that exhausted their retries stay in the outbox with their last error, so nothing is
silently dropped. Admins inspect them here and re-queue once the cause is fixed.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import NotFound
from app.db.models import OutboxEvent


class OpsService:
    def __init__(self, session: AsyncSession, clock: Clock, max_attempts: int) -> None:
        self._session = session
        self._clock = clock
        self._max_attempts = max_attempts

    def _dead(self):
        return (OutboxEvent.processed_at.is_(None), OutboxEvent.attempts >= self._max_attempts)

    async def dead_letters(self, limit: int) -> list[OutboxEvent]:
        query = select(OutboxEvent).where(*self._dead()).order_by(OutboxEvent.created_at).limit(limit)
        return list((await self._session.execute(query)).scalars())

    async def queue_stats(self) -> dict[str, int]:
        pending = await self._session.scalar(
            select(func.count()).where(OutboxEvent.processed_at.is_(None), OutboxEvent.attempts < self._max_attempts)
        )
        dead = await self._session.scalar(select(func.count()).where(*self._dead()))
        return {"pending": int(pending or 0), "dead": int(dead or 0)}

    async def retry(self, event_id: uuid.UUID) -> OutboxEvent:
        result = await self._session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id, OutboxEvent.processed_at.is_(None))
            .values(attempts=0, available_at=self._clock.now(), last_error=None)
            .returning(OutboxEvent)
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise NotFound("No unprocessed event with that id")
        await self._session.commit()
        return event
