"""Infrastructure configuration, read from environment variables / .env.

Business rules (GST, commission, overstay fees, booking limits…) are NOT here: they live
in the `platform_settings` table so an admin can change them at runtime
(see app/services/settings_service.py).
"""

import os
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def normalize_database_url(value: object) -> object:
    """Accept provider connection strings as-is (Neon, Render, Supabase all hand out libpq URLs).

    asyncpg takes `ssl=`, not libpq's `sslmode=`, and rejects `channel_binding=` outright, so a
    pasted `postgresql://…?sslmode=require&channel_binding=require` would fail at first connect.
    """
    if not isinstance(value, str) or not value:
        return value
    url = make_url(value)
    if url.drivername in ("postgres", "postgresql", "postgresql+psycopg2", "postgresql+psycopg"):
        url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    query.pop("channel_binding", None)  # SCRAM channel binding is negotiated by asyncpg itself
    if "sslmode" in query:
        query.setdefault("ssl", query.pop("sslmode"))
    return url.set(query=query).render_as_string(hide_password=False)


def uses_pgbouncer(url: str) -> bool:
    """Neon's pooled endpoint (`*-pooler.*`) is PgBouncer in transaction mode."""
    return "-pooler." in (make_url(url).host or "")


class Settings(BaseSettings):
    # ENV_FILE picks another file, e.g. ENV_FILE=.env.production for the hosted services.
    # env_ignore_empty: `RESEND_WEBHOOK_SECRET=` in a .env means "not configured" (None), never an
    # empty secret — an empty HMAC key would let anyone forge signatures.
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"), env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

    # --- App ---
    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "Parkezy"
    api_public_url: AnyHttpUrl
    app_deep_link_base: str = Field(description="Base URL the mobile app opens, e.g. parkezy://")
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    admin_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)
    default_timezone: str = "Asia/Kolkata"
    trust_forwarded_for: bool = Field(
        default=False, description="Use X-Forwarded-For for client IP (only behind a trusted proxy)"
    )

    # --- Support & legal (shown in the Terms / Privacy Policy and used for support tickets) ---
    support_email: str = "support@parkezy.com"
    legal_entity_name: str = "Parkezy"
    legal_address: str = "Bengaluru, Karnataka, India"
    # Grievance Officer required by the IT Rules 2021 and the DPDP Act 2023; defaults to support.
    grievance_officer_name: str = "Grievance Officer, Parkezy"
    grievance_officer_email: str | None = None

    # --- Database ---
    database_url: str
    # Optional streaming replica for read-heavy discovery (search, listing pages). Empty = primary.
    database_read_url: str | None = None
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_echo: bool = False
    # Recycle before the provider's idle timeout closes the socket under us (Neon, PgBouncer, cloud LBs).
    db_pool_recycle_seconds: int = 300
    # Disable asyncpg statement caching for transaction-mode PgBouncer. Empty = auto-detect `-pooler` hosts.
    db_pgbouncer: bool | None = None
    # Client-side per-statement ceiling (asyncpg command_timeout) so one slow query cannot pin a
    # pooled connection forever. Client-side because PgBouncer drops server startup parameters.
    db_command_timeout_seconds: float = 15.0

    # --- Redis / jobs ---
    redis_url: str
    # Bounded timeouts: the rate limiter and cache fail open on RedisError, which only helps if
    # a hung Redis actually raises instead of stalling every request.
    redis_socket_timeout_seconds: float = 2.0
    redis_health_check_seconds: int = 30
    # Per process. Hosted free tiers cap clients (Redis Cloud free: 30), and API workers, Celery
    # workers and beat all share that budget, so keep each pool small and wait for a free slot.
    redis_max_connections: int = 10
    celery_broker_url: str | None = None
    celery_broker_pool_limit: int = 4
    outbox_sweep_seconds: int = 30
    outbox_batch_size: int = 50
    outbox_max_attempts: int = 10
    outbox_backoff_base_seconds: int = 15
    outbox_backoff_max_seconds: int = 3600
    maintenance_sweep_seconds: int = 60
    cleanup_interval_hours: int = 24
    stale_upload_hours: int = 24

    # --- Auth ---
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "parkezy-api"
    jwt_audience: str = "parkezy-app"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    verification_code_ttl_minutes: int = 15
    verification_code_max_attempts: int = 5
    verification_code_length: int = 6

    # --- Parking access (PIN / QR) ---
    access_code_secret: SecretStr
    access_pin_length: int = 6
    qr_token_ttl_seconds: int = 120

    # --- Rate limits (requests per window) ---
    rate_limit_window_seconds: int = 60
    rate_limit_auth_per_window: int = 10
    rate_limit_access_verify_per_window: int = 20
    rate_limit_default_per_window: int = 120

    # --- Caching / bloom filters ---
    search_cache_ttl_seconds: int = 30
    # geohash-cell caching: cell half-diagonal <= ratio * radius; fetch limit * multiplier candidates per cell
    search_cell_error_ratio: float = 0.25
    search_candidate_multiplier: int = 3
    rules_cache_ttl_seconds: int = 60
    bloom_capacity: int = 1_000_000
    bloom_error_rate: float = 0.001

    # --- Email ---
    email_provider: Literal["resend", "smtp", "console"] = "console"
    email_from: str
    email_reply_to: str | None = None
    resend_api_key: SecretStr | None = None
    resend_api_base: AnyHttpUrl = AnyHttpUrl("https://api.resend.com")
    resend_webhook_secret: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = False

    # --- Object storage (Backblaze B2 S3 API in prod, SeaweedFS locally) ---
    s3_endpoint_url: str
    s3_public_endpoint_url: str | None = Field(
        default=None, description="Endpoint the mobile app can reach, if different (e.g. LAN IP)"
    )
    s3_region: str
    s3_access_key_id: SecretStr
    s3_secret_access_key: SecretStr
    s3_bucket: str
    s3_public_base_url: str | None = Field(
        default=None, description="CDN/public bucket URL for public media; presigned GET if unset"
    )
    s3_presign_ttl_seconds: int = 900
    upload_max_bytes: int = 10 * 1024 * 1024
    upload_allowed_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/heic", "image/webp"]
    )

    # --- Payments ---
    payment_provider: Literal["razorpay", "offline"] = "offline"
    razorpay_key_id: str | None = None
    razorpay_key_secret: SecretStr | None = None
    razorpay_webhook_secret: SecretStr | None = None
    razorpay_api_base: AnyHttpUrl = AnyHttpUrl("https://api.razorpay.com/v1")
    payment_reconcile_interval_seconds: int = 300
    payment_reconcile_after_minutes: int = 5
    payment_abandon_after_minutes: int = 60
    payment_reconcile_batch: int = 100

    # --- Push notifications ---
    push_provider: Literal["expo", "none"] = "none"
    expo_push_url: AnyHttpUrl = AnyHttpUrl("https://exp.host/--/api/v2/push/send")
    expo_access_token: SecretStr | None = None

    # --- External HTTP ---
    http_timeout_seconds: float = 10.0

    # --- Observability ---
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = 0.0
    metrics_token: SecretStr | None = Field(
        default=None, description="Bearer token for GET /metrics; empty disables it"
    )

    _csv = field_validator("cors_origins", "admin_emails", "upload_allowed_types", mode="before")(_split_csv)
    _db_url = field_validator("database_url", "database_read_url", mode="before")(normalize_database_url)

    @field_validator("admin_emails")
    @classmethod
    def _lower(cls, v: list[str]) -> list[str]:
        return [e.lower() for e in v]

    @model_validator(mode="after")
    def _validate_providers(self) -> "Settings":
        if self.email_provider == "resend" and not self.resend_api_key:
            raise ValueError("EMAIL_PROVIDER=resend requires RESEND_API_KEY")
        if self.email_provider == "smtp" and not self.smtp_host:
            raise ValueError("EMAIL_PROVIDER=smtp requires SMTP_HOST")
        if self.payment_provider == "razorpay" and not (
            self.razorpay_key_id and self.razorpay_key_secret and self.razorpay_webhook_secret
        ):
            raise ValueError(
                "PAYMENT_PROVIDER=razorpay requires RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET and RAZORPAY_WEBHOOK_SECRET"
            )
        if self.app_env == "production":
            for name in ("jwt_secret", "access_code_secret"):
                if len(getattr(self, name).get_secret_value()) < 32:
                    raise ValueError(f"{name.upper()} must be at least 32 characters in production")
            if self.email_provider == "console":
                raise ValueError("EMAIL_PROVIDER=console is not allowed in production")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS=* is not allowed in production; list the allowed origins")
        return self

    def pgbouncer_for(self, url: str) -> bool:
        return self.db_pgbouncer if self.db_pgbouncer is not None else uses_pgbouncer(url)

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
