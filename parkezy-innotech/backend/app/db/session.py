import uuid
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings


def connect_args(settings: Settings, url: str) -> dict:
    args: dict = {"command_timeout": settings.db_command_timeout_seconds}
    if settings.pgbouncer_for(url):
        # Transaction-mode PgBouncer hands each transaction a different server connection, so a
        # statement prepared on one is missing (or clashes by name) on the next. SQLAlchemy's recipe:
        # no statement caches and unique statement names.
        args |= {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        }
    return args


def create_engine(settings: Settings, *, pooled: bool = True, url: str | None = None) -> AsyncEngine:
    url = url or settings.database_url
    kwargs: dict = {
        "echo": settings.db_echo,
        "pool_pre_ping": True,
        "connect_args": connect_args(settings, url),
    }
    if pooled:
        kwargs |= {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_recycle": settings.db_pool_recycle_seconds,
        }
    else:
        kwargs["poolclass"] = NullPool
    return create_async_engine(url, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def session_scope(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
