"""Background jobs as plain async functions of the container: Celery calls them in
production, tests call them directly."""

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from app.container import Container
from app.core.errors import ExternalServiceError
from app.db.models import RefreshToken, Upload, VerificationCode
from app.domain.enums import UploadStatus
from app.services.factory import Services
from app.workers.runtime import outbox_processor

log = logging.getLogger(__name__)


async def process_outbox(c: Container) -> int:
    return await outbox_processor(c).drain()


async def maintenance(c: Container) -> dict:
    async with c.session_factory() as session:
        services = Services(c, session)
        rules = await services.settings().rules()
        bookings = services.bookings()
        result = {
            "expired": await bookings.expire_stale(),
            "no_shows": await bookings.expire_no_shows(),
            "reminders": await bookings.send_ending_reminders(rules),
        }
    result["events"] = await process_outbox(c)
    return result


async def reconcile_payments(c: Container) -> dict:
    s = c.settings
    async with c.session_factory() as session:
        result = (
            await Services(c, session)
            .payments()
            .reconcile(
                check_after=timedelta(minutes=s.payment_reconcile_after_minutes),
                abandon_after=timedelta(minutes=s.payment_abandon_after_minutes),
                batch=s.payment_reconcile_batch,
            )
        )
    await process_outbox(c)
    return result


async def refund_payment(c: Container, payment_id: str, amount: str) -> None:
    async with c.session_factory() as session:
        await Services(c, session).payments().refund(uuid.UUID(payment_id), Decimal(amount))


async def cleanup(c: Container) -> dict:
    now = c.clock.now()
    stale_before = now - timedelta(hours=c.settings.stale_upload_hours)
    async with c.session_factory() as session:
        tokens = await session.execute(delete(RefreshToken).where(RefreshToken.expires_at < now))
        codes = await session.execute(delete(VerificationCode).where(VerificationCode.expires_at < now))
        stale = list(
            (
                await session.execute(
                    select(Upload).where(Upload.status == UploadStatus.PENDING.value, Upload.created_at < stale_before)
                )
            ).scalars()
        )
        removed = 0
        for upload in stale:
            try:
                await c.storage.delete(upload.storage_key)
            except ExternalServiceError:
                log.warning("could not delete stale object %s", upload.storage_key)
                continue
            await session.delete(upload)
            removed += 1
        await session.commit()
    return {"refresh_tokens": tokens.rowcount, "codes": codes.rowcount, "uploads": removed}
