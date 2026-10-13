import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import ExternalServiceError
from app.db.models import EmailLog, EmailSuppression
from app.domain.enums import EmailStatus
from app.integrations.email import EmailRenderer, EmailSender, OutgoingEmail

log = logging.getLogger(__name__)

# Resend webhook event -> (our status, suppress future sends?)
RESEND_EVENTS: dict[str, tuple[EmailStatus, bool]] = {
    "email.delivered": (EmailStatus.DELIVERED, False),
    "email.bounced": (EmailStatus.BOUNCED, True),
    "email.complained": (EmailStatus.COMPLAINED, True),
}


class EmailService:
    def __init__(self, session: AsyncSession, sender: EmailSender, renderer: EmailRenderer, clock: Clock) -> None:
        self._session = session
        self._sender = sender
        self._renderer = renderer
        self._clock = clock

    async def send(
        self, *, to: str, template: str, context: dict, dedupe_key: str, user_id: uuid.UUID | None = None
    ) -> EmailStatus:
        """Idempotent per dedupe_key: retries of the same event never send twice."""
        record = (
            await self._session.execute(select(EmailLog).where(EmailLog.dedupe_key == dedupe_key).with_for_update())
        ).scalar_one_or_none()
        if record and record.status not in (EmailStatus.QUEUED.value, EmailStatus.FAILED.value):
            return EmailStatus(record.status)
        if record is None:
            record = EmailLog(
                user_id=user_id, to_email=to, template=template, dedupe_key=dedupe_key, status=EmailStatus.QUEUED.value
            )
            self._session.add(record)
            await self._session.flush()
        if await self._session.get(EmailSuppression, to.lower()):
            record.status = EmailStatus.SKIPPED.value
            record.error = "suppressed"
            await self._session.commit()
            return EmailStatus.SKIPPED
        rendered = self._renderer.render(template, context)
        try:
            message_id = await self._sender.send(
                OutgoingEmail(
                    to=to,
                    subject=rendered.subject,
                    html=rendered.html,
                    text=rendered.text,
                    idempotency_key=dedupe_key,
                    tags={"template": template},
                )
            )
        except ExternalServiceError as e:
            record.status = EmailStatus.FAILED.value
            record.error = f"{e.message}: {e.details}"[:1000]
            await self._session.commit()
            raise
        record.status = EmailStatus.SENT.value
        record.provider_message_id = message_id
        record.error = None
        await self._session.commit()
        return EmailStatus.SENT

    async def apply_provider_event(self, event_type: str, data: dict) -> None:
        mapping = RESEND_EVENTS.get(event_type)
        if mapping is None:
            return
        status, suppress = mapping
        message_id = data.get("email_id")
        if message_id:
            record = (
                await self._session.execute(select(EmailLog).where(EmailLog.provider_message_id == message_id))
            ).scalar_one_or_none()
            if record:
                record.status = status.value
        if suppress:
            for address in data.get("to", []):
                await self._session.execute(
                    insert(EmailSuppression)
                    .values(email=address.lower(), reason=status.value, created_at=self._clock.now())
                    .on_conflict_do_nothing()
                )
        await self._session.commit()
