import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import Container
from app.core.errors import Forbidden, Unauthorized
from app.db.models import User
from app.domain.enums import UserStatus
from app.domain.rules import PlatformRules
from app.services.factory import Services
from app.services.outbox import OUTBOX_DIRTY

log = logging.getLogger(__name__)
OUTBOX_WAKE = "outbox_wake"

bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def _mark_wake(session) -> None:
    if session.info.pop(OUTBOX_DIRTY, False):
        session.info[OUTBOX_WAKE] = True


async def get_session(c: ContainerDep) -> AsyncIterator[AsyncSession]:
    async with c.session_factory() as session:
        event.listen(session.sync_session, "after_commit", _mark_wake)
        try:
            yield session
        finally:
            if session.info.pop(OUTBOX_WAKE, False):
                try:
                    # Wake a worker now; the periodic sweep is the safety net if this fails.
                    await asyncio.to_thread(c.jobs.enqueue, "process_outbox")
                except Exception:  # noqa: BLE001
                    log.warning("could not enqueue outbox processing", exc_info=True)


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_services(c: ContainerDep, session: SessionDep) -> Services:
    return Services(c, session)


ServicesDep = Annotated[Services, Depends(get_services)]


async def get_read_services(c: ContainerDep) -> AsyncIterator[Services]:
    """Services bound to the read replica (or the primary when none is configured).
    Only for side-effect-free endpoints: never write through these."""
    async with c.read_session_factory() as session:
        yield Services(c, session)


ReadServicesDep = Annotated[Services, Depends(get_read_services)]


async def get_rules(services: ServicesDep) -> PlatformRules:
    return await services.settings().rules()


RulesDep = Annotated[PlatformRules, Depends(get_rules)]


async def get_current_user(
    services: ServicesDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if credentials is None:
        raise Unauthorized("Sign in required", code="not_authenticated")
    user_id, token_version = services.auth().access_claims(credentials.credentials)
    user = await services.session.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise Unauthorized("Account unavailable", code="account_inactive")
    if token_version != user.token_version:
        raise Unauthorized("Session expired, please sign in again", code="session_revoked")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    services: ServicesDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User | None:
    """The signed-in user, or None when no token is sent. A token that IS sent must be valid."""
    if credentials is None:
        return None
    return await get_current_user(services, credentials)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def get_host(user: CurrentUser) -> User:
    if not user.is_host:
        raise Forbidden("Host account required", code="not_a_host")
    return user


async def get_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise Forbidden("Admin only", code="admin_only")
    return user


HostUser = Annotated[User, Depends(get_host)]
AdminUser = Annotated[User, Depends(get_admin)]


def client_ip(request: Request, c: Container) -> str:
    if c.settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # The proxy APPENDS the address it saw, so the last entry is the only one a client can't forge.
            # (The first entry is whatever the client sent, which would let anyone dodge rate limits.)
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class RateLimit:
    """Dependency: `Depends(RateLimit("login", "rate_limit_auth_per_window"))`.
    Sets X-RateLimit-* headers so clients can back off before they are throttled."""

    def __init__(self, bucket: str, limit_setting: str) -> None:
        self.bucket = bucket
        self.limit_setting = limit_setting

    async def _apply(self, c: Container, identity: str, response: Response) -> None:
        status = await c.rate_limiter.hit(
            self.bucket, identity, getattr(c.settings, self.limit_setting), c.settings.rate_limit_window_seconds
        )
        response.headers["X-RateLimit-Limit"] = str(status.limit)
        response.headers["X-RateLimit-Remaining"] = str(status.remaining)
        response.headers["X-RateLimit-Reset"] = str(status.reset_seconds)

    async def __call__(self, request: Request, response: Response, c: ContainerDep) -> None:
        await self._apply(c, client_ip(request, c), response)


class UserRateLimit(RateLimit):
    async def __call__(self, request: Request, response: Response, c: ContainerDep, user: CurrentUser) -> None:  # type: ignore[override]
        await self._apply(c, str(user.id), response)


def page_limit(rules: PlatformRules, requested: int | None) -> int:
    return min(requested or rules.default_page_size, rules.max_page_size)
