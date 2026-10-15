import asyncio
import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import ContainerDep
from app.container import Container
from app.core.security import constant_time_equals
from app.infra import metrics
from app.services.factory import Services

log = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict:
    """Liveness: the process is up and its event loop answers. Touches no dependency on purpose, so a
    database or Redis outage never makes the platform restart healthy instances."""
    return {"status": "ok"}


async def _check_database(c: Container) -> str:
    pool = c.engine.pool
    size, overflow = getattr(pool, "size", lambda: 0)(), getattr(pool, "_max_overflow", 0)
    checked_out = getattr(pool, "checkedout", lambda: 0)()  # QueuePool only; NullPool never saturates
    if size and checked_out >= size + max(overflow, 0):
        # Every connection is in use by requests that are being served: busy, not broken. Waiting
        # for one here would mark every loaded instance unready at once and turn load into an outage.
        return "busy"
    async with c.engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return "ok"


async def _check_redis(c: Container) -> str:
    await c.redis.ping()
    return "ok"


async def _bounded(check, c: Container) -> str:
    try:
        async with asyncio.timeout(c.settings.health_check_timeout_seconds):
            return await check(c)
    except TimeoutError:
        return "error: timeout"
    except Exception as e:  # noqa: BLE001 - reported in the response, never hidden
        return f"error: {type(e).__name__}"


@router.get("/health/ready")
async def ready(c: ContainerDep) -> JSONResponse:
    """Readiness: can this instance serve traffic right now?

    The database is required: without it almost no endpoint works, so the instance reports 503 and
    the load balancer should stop routing to it. Redis is reported but not required: the cache and
    rate limiter degrade without it and requests are still served, so pulling every instance out of
    rotation over a Redis blip would cause a full outage. Each check is bounded by
    health_check_timeout_seconds, so the probe always answers quickly.
    """
    database, redis = await asyncio.gather(_bounded(_check_database, c), _bounded(_check_redis, c))
    checks = {"database": database, "redis": redis}
    serving = database in ("ok", "busy")
    status = "ok" if serving and redis == "ok" and database == "ok" else ("degraded" if serving else "unavailable")
    return JSONResponse({"status": status, "checks": checks}, status_code=200 if serving else 503)


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics(request: Request, c: ContainerDep) -> Response:
    token = c.settings.metrics_token
    if token is None:
        return Response(status_code=404)
    if not constant_time_equals(request.headers.get("authorization", ""), f"Bearer {token.get_secret_value()}"):
        return Response(status_code=401)

    async def queue_stats() -> dict[str, int]:
        async with c.session_factory() as session:
            return await Services(c, session).ops().queue_stats()

    # Request metrics come from memory and must stay scrapeable during a database outage (that is when
    # they matter most). Outbox numbers need the database; when it can't answer, they are omitted and
    # parkezy_outbox_stats_up says so, rather than reporting a made-up zero.
    try:
        stats: dict[str, int] | None = await asyncio.wait_for(queue_stats(), c.settings.health_check_timeout_seconds)
    except Exception as e:  # noqa: BLE001 - surfaced as parkezy_outbox_stats_up 0 and logged
        log.warning("metrics: outbox stats unavailable: %s", type(e).__name__)
        stats = None
    body, content_type = metrics.render(stats)
    return Response(body, media_type=content_type)
