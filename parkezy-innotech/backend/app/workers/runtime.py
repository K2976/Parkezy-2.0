"""Async runtime for Celery workers: one event loop and one container per worker process."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.container import Container, build_container
from app.core.config import get_settings
from app.services.factory import Services
from app.workers.handlers import HandlerContext
from app.workers.outbox_processor import OutboxProcessor

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_container: Container | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def container() -> Container:
    global _container
    if _container is None:
        from app.workers.celery_app import CeleryJobQueue

        _container = build_container(get_settings(), jobs=CeleryJobQueue())
    return _container


def run[T](fn: Callable[[Container], Awaitable[T]]) -> T:
    return _get_loop().run_until_complete(fn(container()))


def handler_context(c: Container, session) -> HandlerContext:
    services = Services(c, session)
    return HandlerContext(
        session=session,
        settings=c.settings,
        notifications=services.notifications(),
        email=services.email(),
        bookings=services.bookings(),
        payments=services.payments(),
    )


def outbox_processor(c: Container) -> OutboxProcessor:
    s = c.settings
    return OutboxProcessor(
        c.session_factory,
        c.clock,
        lambda session: handler_context(c, session),
        batch_size=s.outbox_batch_size,
        max_attempts=s.outbox_max_attempts,
        backoff_base_seconds=s.outbox_backoff_base_seconds,
        backoff_max_seconds=s.outbox_backoff_max_seconds,
    )
