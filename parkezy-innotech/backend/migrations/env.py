import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import normalize_database_url
from app.db import models  # noqa: F401  (registers tables on metadata)
from app.db.base import Base

target_metadata = Base.metadata


def _database_url() -> str:
    url = context.config.attributes.get("database_url") or os.environ.get("DATABASE_URL")
    if not url:
        from app.core.config import get_settings

        url = get_settings().database_url
    # DDL goes to Neon's direct endpoint, not the transaction-mode PgBouncer in front of it.
    return str(normalize_database_url(url)).replace("-pooler.", ".", 1)


def run_migrations_offline() -> None:
    context.configure(url=_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
