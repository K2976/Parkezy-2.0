"""Delivers outbox events to handlers.

Claiming uses a lease: pending rows are locked with SKIP LOCKED and their `available_at` is
pushed forward, so concurrent workers never process the same event at the same time. A
crash simply lets the lease run out and the event is retried (handlers are idempotent).
"""

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.db.models import OutboxEvent
from app.workers.handlers import HANDLERS, HandlerContext

log = logging.getLogger(__name__)

SENSITIVE_KEYS = ("code",)


def backoff(attempts: int, base_seconds: int, max_seconds: int) -> timedelta:
    return timedelta(seconds=min(base_seconds * 2 ** max(attempts - 1, 0), max_seconds))


class OutboxProcessor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Clock,
        context_factory: Callable[[AsyncSession], HandlerContext],
        *,
        batch_size: int,
        max_attempts: int,
        backoff_base_seconds: int,
        backoff_max_seconds: int,
    ) -> None:
        self._sessions = session_factory
        self._clock = clock
        self._context_factory = context_factory
        self._batch = batch_size
        self._max_attempts = max_attempts
        self._base = backoff_base_seconds
        self._max = backoff_max_seconds

    async def _claim(self) -> list[OutboxEvent]:
        async with self._sessions() as session:
            now = self._clock.now()
            rows = list(
                (
                    await session.execute(
                        select(OutboxEvent)
                        .where(
                            OutboxEvent.processed_at.is_(None),
                            OutboxEvent.available_at <= now,
                            OutboxEvent.attempts < self._max_attempts,
                        )
                        .order_by(OutboxEvent.available_at)
                        .limit(self._batch)
                        .with_for_update(skip_locked=True)
                    )
                ).scalars()
            )
            for row in rows:
                row.attempts += 1
                row.available_at = now + backoff(row.attempts, self._base, self._max)
            await session.commit()
            return rows

    async def _finish(self, event_id: uuid.UUID, payload: dict, error: str | None) -> None:
        async with self._sessions() as session:
            values: dict = {"last_error": error}
            if error is None:
                values["processed_at"] = self._clock.now()
                values["payload"] = {k: v for k, v in payload.items() if k not in SENSITIVE_KEYS}
            await session.execute(update(OutboxEvent).where(OutboxEvent.id == event_id).values(**values))
            await session.commit()

    async def run_once(self) -> int:
        events = await self._claim()
        for event in events:
            handler: Callable[..., Awaitable[None]] | None = HANDLERS.get(event.type)
            if handler is None:
                await self._finish(event.id, event.payload, f"no handler for {event.type}")
                log.error("no handler registered for outbox event %s", event.type)
                continue
            try:
                async with self._sessions() as session:
                    await handler(self._context_factory(session), str(event.id), event.payload)
            except Exception as e:  # noqa: BLE001 - any failure is retried with backoff
                log.exception("outbox event %s (%s) failed", event.id, event.type)
                await self._finish(event.id, event.payload, f"{type(e).__name__}: {e}"[:2000])
            else:
                await self._finish(event.id, event.payload, None)
        return len(events)

    async def drain(self, max_rounds: int = 20) -> int:
        total = 0
        for _ in range(max_rounds):
            handled = await self.run_once()
            total += handled
            if handled < self._batch:
                break
        return total
