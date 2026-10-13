import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.errors import install_error_handlers
from app.api.middleware import RequestContextMiddleware
from app.api.v1 import admin, auth, bookings, health, host, me, misc, public, webhooks
from app.container import Container, build_container
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.integrations.storage import S3ObjectStorage

log = logging.getLogger(__name__)


def _init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )


def _default_container(settings: Settings) -> Container:
    from app.workers.celery_app import CeleryJobQueue

    return build_container(settings, jobs=CeleryJobQueue())


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    _init_sentry(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or _default_container(settings)
        storage = app.state.container.storage
        if settings.app_env in ("local", "test") and isinstance(storage, S3ObjectStorage):
            try:
                await storage.ensure_bucket()
            except Exception:  # noqa: BLE001 - dev convenience only
                log.warning("could not ensure local bucket", exc_info=True)
        yield
        if container is None:
            await app.state.container.aclose()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=False,
        )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    for module in (auth, me, public, bookings, host, misc, admin, webhooks):
        v1.include_router(module.router)
    app.include_router(v1)
    app.include_router(health.router)
    return app


app = create_app()
