"""Composition root: builds every long-lived dependency from Settings, exactly once.

Services never construct their own collaborators; they receive them from here (API via
app/api/deps.py, workers via app/workers/runtime.py). Tests swap pieces by passing overrides.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from redis.asyncio import BlockingConnectionPool, Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.clock import Clock, SystemClock
from app.core.config import Settings
from app.core.security import PasswordHasher, TokenService
from app.db.session import create_engine, create_session_factory
from app.domain.access import AccessCodeService
from app.infra.bloom import BloomFilter
from app.infra.cache import Cache
from app.infra.one_time import OneTimeTokenRegistry
from app.infra.rate_limit import RateLimiter
from app.integrations.challenge import ChallengeVerifier, NoChallengeVerifier, TurnstileVerifier
from app.integrations.email import (
    ConsoleEmailSender,
    EmailRenderer,
    EmailSender,
    ResendEmailSender,
    SmtpEmailSender,
)
from app.integrations.identity import IdentityVerifier, OidcIdentityVerifier
from app.integrations.payments import PaymentGateway, RazorpayGateway
from app.integrations.push import ExpoPushSender, NoopPushSender, PushSender
from app.integrations.storage import ObjectStorage, S3ObjectStorage
from app.services.jobs import JobQueue
from app.services.login_protection import LoginProtection

TEMPLATE_DIR = Path(__file__).parent / "templates" / "emails"


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    read_engine: AsyncEngine
    read_session_factory: async_sessionmaker[AsyncSession]
    redis: Redis
    http: httpx.AsyncClient
    clock: Clock
    hasher: PasswordHasher
    tokens: TokenService
    access_codes: AccessCodeService
    cache: Cache
    rate_limiter: RateLimiter
    one_time: OneTimeTokenRegistry
    webhook_bloom: BloomFilter
    storage: ObjectStorage
    payment_gateway: PaymentGateway | None
    email_sender: EmailSender
    email_renderer: EmailRenderer
    push_sender: PushSender
    jobs: JobQueue
    identity_verifier: IdentityVerifier | None = None
    login_guard: LoginProtection | None = None
    extras: dict = field(default_factory=dict)

    async def aclose(self) -> None:
        await self.http.aclose()
        await self.redis.aclose()
        await self.engine.dispose()
        if self.read_engine is not self.engine:
            await self.read_engine.dispose()


def _email_sender(s: Settings, http: httpx.AsyncClient) -> EmailSender:
    if s.email_provider == "resend":
        assert s.resend_api_key
        return ResendEmailSender(
            http, str(s.resend_api_base), s.resend_api_key.get_secret_value(), s.email_from, s.email_reply_to
        )
    if s.email_provider == "smtp":
        assert s.smtp_host
        return SmtpEmailSender(
            host=s.smtp_host,
            port=s.smtp_port,
            sender=s.email_from,
            reply_to=s.email_reply_to,
            username=s.smtp_username,
            password=s.smtp_password.get_secret_value() if s.smtp_password else None,
            use_tls=s.smtp_use_tls,
            timeout=s.http_timeout_seconds,
        )
    return ConsoleEmailSender()


def _payment_gateway(s: Settings, http: httpx.AsyncClient) -> PaymentGateway | None:
    if s.payment_provider == "razorpay":
        assert s.razorpay_key_id and s.razorpay_key_secret and s.razorpay_webhook_secret
        return RazorpayGateway(
            http,
            str(s.razorpay_api_base),
            s.razorpay_key_id,
            s.razorpay_key_secret.get_secret_value(),
            s.razorpay_webhook_secret.get_secret_value(),
        )
    return None


def _push_sender(s: Settings, http: httpx.AsyncClient) -> PushSender:
    if s.push_provider == "expo":
        token = s.expo_access_token.get_secret_value() if s.expo_access_token else None
        return ExpoPushSender(http, str(s.expo_push_url), token)
    return NoopPushSender()


def _challenge_verifier(s: Settings, http: httpx.AsyncClient) -> ChallengeVerifier:
    if s.login_challenge_provider == "turnstile":
        assert s.turnstile_site_key and s.turnstile_secret_key
        return TurnstileVerifier(
            http,
            verify_url=str(s.turnstile_verify_url),
            secret_key=s.turnstile_secret_key.get_secret_value(),
            site_key=s.turnstile_site_key,
            expected_hostnames=s.login_challenge_expected_hostnames,
            expected_action=s.login_challenge_action or None,
            max_age_seconds=s.login_challenge_max_age_seconds,
        )
    return NoChallengeVerifier()


def build_container(settings: Settings, *, jobs: JobQueue, pooled_db: bool = True, **overrides) -> Container:
    engine = create_engine(settings, pooled=pooled_db)
    read_engine = (
        create_engine(settings, pooled=pooled_db, url=settings.database_read_url)
        if settings.database_read_url
        else engine
    )
    # from_pool hands ownership to the client, so Container.aclose() also closes the pool.
    redis = Redis.from_pool(
        BlockingConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            timeout=settings.redis_socket_timeout_seconds,  # wait this long for a free pooled connection
            socket_timeout=settings.redis_socket_timeout_seconds,
            socket_connect_timeout=settings.redis_socket_timeout_seconds,
            health_check_interval=settings.redis_health_check_seconds,
            decode_responses=False,
        )
    )
    http = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
    clock: Clock = overrides.pop("clock", None) or SystemClock()
    parts: dict = dict(
        settings=settings,
        engine=engine,
        session_factory=create_session_factory(engine),
        read_engine=read_engine,
        read_session_factory=create_session_factory(read_engine),
        redis=redis,
        http=http,
        clock=clock,
        hasher=PasswordHasher(max_concurrency=settings.password_hash_concurrency),
        tokens=TokenService(
            settings.jwt_secret.get_secret_value(),
            settings.jwt_algorithm,
            settings.jwt_issuer,
            settings.jwt_audience,
            clock,
        ),
        access_codes=AccessCodeService(settings.access_code_secret.get_secret_value(), settings.access_pin_length),
        cache=Cache(redis),
        rate_limiter=RateLimiter(redis),
        one_time=OneTimeTokenRegistry(redis),
        webhook_bloom=BloomFilter(redis, "bloom:webhooks", settings.bloom_capacity, settings.bloom_error_rate),
        storage=S3ObjectStorage(
            endpoint_url=settings.s3_endpoint_url,
            public_endpoint_url=settings.s3_public_endpoint_url,
            region=settings.s3_region,
            access_key_id=settings.s3_access_key_id.get_secret_value(),
            secret_access_key=settings.s3_secret_access_key.get_secret_value(),
            bucket=settings.s3_bucket,
            presign_ttl_seconds=settings.s3_presign_ttl_seconds,
            public_base_url=settings.s3_public_base_url,
        ),
        payment_gateway=_payment_gateway(settings, http),
        email_sender=_email_sender(settings, http),
        email_renderer=EmailRenderer(
            TEMPLATE_DIR,
            {"app_name": settings.app_name, "deep_link_base": settings.app_deep_link_base},
        ),
        push_sender=_push_sender(settings, http),
        jobs=jobs,
        identity_verifier=OidcIdentityVerifier(
            http, google_client_ids=settings.google_client_ids, apple_client_ids=settings.apple_client_ids
        ),
    )
    challenge = overrides.pop("challenge_verifier", None) or _challenge_verifier(settings, http)
    parts.update(overrides)
    parts.setdefault(
        "login_guard", LoginProtection(settings, parts["redis"], parts["one_time"], challenge, now=time.time)
    )
    return Container(**parts)
