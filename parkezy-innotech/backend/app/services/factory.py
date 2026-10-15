"""Builds request/task-scoped services from the container and a DB session.
Shared by the API (app/api/deps.py) and the workers so wiring lives in one place."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.container import Container
from app.services.admin_user_service import AdminUserService
from app.services.auth_service import AuthService
from app.services.booking_service import BookingService
from app.services.dispute_service import DisputeService
from app.services.email_service import EmailService
from app.services.favorite_service import FavoriteService
from app.services.host_service import HostDashboardService
from app.services.listing_service import ListingService
from app.services.notification_service import NotificationService
from app.services.ops_service import OpsService
from app.services.payment_service import PaymentService
from app.services.payout_service import PayoutService
from app.services.receipt_service import ReceiptService
from app.services.review_service import ReviewService
from app.services.settings_service import SettingsService
from app.services.support_service import SupportService
from app.services.upload_service import UploadService
from app.services.user_service import UserService


class Services:
    def __init__(self, c: Container, session: AsyncSession) -> None:
        self.c = c
        self.session = session

    def settings(self) -> SettingsService:
        return SettingsService(self.session, self.c.cache, self.c.clock, self.c.settings.rules_cache_ttl_seconds)

    def auth(self) -> AuthService:
        return AuthService(self.session, self.c.settings, self.c.hasher, self.c.tokens, self.c.clock)

    def users(self) -> UserService:
        return UserService(self.session, self.c.clock, self.auth(), self.c.cache)

    def uploads(self) -> UploadService:
        return UploadService(self.session, self.c.storage, self.c.settings, self.c.clock)

    def listings(self) -> ListingService:
        return ListingService(self.session, self.c.settings, self.c.clock, self.c.cache, self.c.storage, self.uploads())

    def bookings(self) -> BookingService:
        return BookingService(
            self.session,
            self.c.settings,
            self.c.clock,
            self.c.cache,
            self.c.tokens,
            self.c.access_codes,
            self.c.one_time,
            online_payments=self.c.payment_gateway is not None,
        )

    def payments(self) -> PaymentService:
        return PaymentService(
            self.session, self.c.payment_gateway, self.bookings(), self.c.clock, self.c.webhook_bloom, self.c.jobs
        )

    def email(self) -> EmailService:
        return EmailService(self.session, self.c.email_sender, self.c.email_renderer, self.c.clock)

    def notifications(self) -> NotificationService:
        return NotificationService(self.session, self.c.clock, self.c.push_sender, self.email())

    def disputes(self) -> DisputeService:
        return DisputeService(self.session, self.c.clock, self.uploads())

    def host_dashboard(self) -> HostDashboardService:
        return HostDashboardService(self.session, self.c.clock)

    def ops(self) -> OpsService:
        return OpsService(self.session, self.c.clock, self.c.settings.outbox_max_attempts)

    def support(self) -> SupportService:
        return SupportService(self.session, self.c.clock)

    def reviews(self) -> ReviewService:
        return ReviewService(self.session, self.c.clock, self.c.cache)

    def favorites(self) -> FavoriteService:
        return FavoriteService(self.session, self.c.clock)

    def payouts(self) -> PayoutService:
        return PayoutService(self.session, self.c.clock)

    def receipts(self) -> ReceiptService:
        return ReceiptService(self.session, self.c.clock, self.bookings(), self.c.settings.default_timezone)

    def admin_users(self) -> AdminUserService:
        return AdminUserService(self.session, self.c.clock, self.auth(), self.c.cache)
