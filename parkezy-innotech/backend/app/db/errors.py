"""Recognise transient database failures so the API can answer 503 (retry later) instead of 500.

Only failures that are about the database being busy or unreachable qualify: pool exhausted,
connection refused/lost, statement timed out, lock wait timed out, deadlock. Programming errors,
constraint violations and bad data are NOT transient and stay 500s (or are handled earlier as
409/422 by the services). Nothing is swallowed: the request has already failed and its
transaction is rolled back when the session closes; this only chooses an honest status code.
"""

import asyncio
from dataclasses import dataclass
from types import TracebackType

import asyncpg.exceptions as pg  # type: ignore[import-untyped]
from sqlalchemy import exc as sa


@dataclass(frozen=True)
class DatabaseFailure:
    code: str  # database_busy | database_unavailable
    message: str
    reason: str  # short machine-readable cause, logged and returned in details


BUSY = "database_busy"
UNAVAILABLE = "database_unavailable"
_BUSY_MSG = "We're handling a lot of requests right now. Please try again in a few seconds."
_DOWN_MSG = "We can't reach our database right now. Please try again in a few seconds."

_CONNECTION_ERRORS = (
    pg.PostgresConnectionError,  # connection does not exist / failure / rejected
    pg.CannotConnectNowError,  # server starting up or shutting down
    pg.TooManyConnectionsError,
    pg.AdminShutdownError,
    pg.CrashShutdownError,
    pg.InterfaceError,  # e.g. "connection is closed"
    ConnectionError,  # refused / reset at the socket level
    OSError,  # DNS failure, network unreachable
)
_CONTENTION_ERRORS = (
    pg.QueryCanceledError,  # server-side statement_timeout
    pg.LockNotAvailableError,  # lock_timeout
    pg.DeadlockDetectedError,
    pg.SerializationError,
)


def _chain(exc: BaseException, limit: int = 8):
    """The exception, what it wraps (SQLAlchemy's .orig) and what caused it."""
    seen: set[int] = set()
    todo: list[BaseException] = [exc]
    while todo and len(seen) < limit:
        current = todo.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        todo += [e for e in (getattr(current, "orig", None), current.__cause__, current.__context__) if e is not None]


def _driver_modules(tb: TracebackType | None) -> list[str]:
    modules = []
    while tb is not None:
        modules.append(tb.tb_frame.f_globals.get("__name__", ""))
        tb = tb.tb_next
    return modules


def _raised_in_db_driver(tb: TracebackType | None) -> bool:
    """True when the traceback passes through asyncpg or SQLAlchemy (so a bare TimeoutError/OSError
    really came from talking to the database, not from e.g. an HTTP client or Redis)."""
    return any(m.startswith(("asyncpg", "sqlalchemy")) for m in _driver_modules(tb))


def _while_connecting(err: BaseException) -> bool:
    """The timeout fired while opening a connection. asyncpg's connect() wraps the handshake in a
    timeout, so the handshake frames (connect_utils) are on the cancelled inner task it chains to."""
    current: BaseException | None = err
    for _ in range(4):
        if current is None:
            return False
        if any(m.startswith("asyncpg.connect_utils") for m in _driver_modules(current.__traceback__)):
            return True
        current = current.__context__
    return False


# Exception types the API routes through classify(); anything not transient is re-raised -> 500.
HANDLED_TYPES: tuple[type[Exception], ...] = (sa.SQLAlchemyError, pg.PostgresError, pg.InterfaceError, OSError)


def classify(exc: BaseException) -> DatabaseFailure | None:
    for err in _chain(exc):
        if isinstance(err, sa.TimeoutError):  # QueuePool limit reached, waited pool_timeout
            return DatabaseFailure(BUSY, _BUSY_MSG, "pool_exhausted")
        if isinstance(err, _CONTENTION_ERRORS):
            return DatabaseFailure(BUSY, _BUSY_MSG, type(err).__name__)
        if isinstance(err, sa.DBAPIError) and err.connection_invalidated:
            return DatabaseFailure(UNAVAILABLE, _DOWN_MSG, "connection_lost")
        if isinstance(err, pg.PostgresError) and not isinstance(err, _CONNECTION_ERRORS):
            return None  # a real SQL error (constraint, syntax, bad data): not transient
        if isinstance(err, (TimeoutError, asyncio.TimeoutError)) and _raised_in_db_driver(err.__traceback__):
            if _while_connecting(err):
                return DatabaseFailure(UNAVAILABLE, _DOWN_MSG, "connect_timeout")
            return DatabaseFailure(BUSY, _BUSY_MSG, "statement_timeout")
        if isinstance(err, _CONNECTION_ERRORS) and (
            isinstance(err, pg.PostgresError) or _raised_in_db_driver(err.__traceback__)
        ):
            return DatabaseFailure(UNAVAILABLE, _DOWN_MSG, type(err).__name__)
    return None
