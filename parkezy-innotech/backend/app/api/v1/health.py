from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import ContainerDep
from app.core.security import constant_time_equals
from app.infra import metrics
from app.services.factory import Services

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(c: ContainerDep) -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        async with c.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["database"] = f"error: {type(e).__name__}"
    try:
        await c.redis.ping()
        checks["redis"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["redis"] = f"error: {type(e).__name__}"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks}, status_code=200 if healthy else 503
    )


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics(request: Request, c: ContainerDep) -> Response:
    token = c.settings.metrics_token
    if token is None:
        return Response(status_code=404)
    if not constant_time_equals(request.headers.get("authorization", ""), f"Bearer {token.get_secret_value()}"):
        return Response(status_code=401)
    async with c.session_factory() as session:
        stats = await Services(c, session).ops().queue_stats()
    metrics.OUTBOX_PENDING.set(stats["pending"])
    metrics.OUTBOX_DEAD.set(stats["dead"])
    body, content_type = metrics.render()
    return Response(body, media_type=content_type)
