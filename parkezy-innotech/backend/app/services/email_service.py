import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import ExternalServiceError
from app.db.models import EmailLog, EmailSuppression
from app.domain.enums import EmailStatus
from app.integrations.email import EmailRenderer, EmailSender, OutgoingEmail, PermanentEmailError

log = logging.getLogger(__name__)

# Resend webhook event -> (our status, suppress future sends?). Opens/clicks are not tracked;
# delivery_delayed is transient and followed by delivered/bounced.
RESEND_EVENTS: dict[str, tuple[EmailStatus, bool]] = {
    "email.delivered": (EmailStatus.DELIVERED, False),
    "email.bounced": (EmailStatus.BOUNCED, True),
    "email.complained": (EmailStatus.COMPLAINED, True),
    "email.failed": (EmailStatus.FAILED, False),
    "email.suppressed": (EmailStatus.SKIPPED, True),  # Resend refused: address is on its suppression list
}
# Webhooks can arrive late, twice or out of order: a status only ever moves forward, so a
# replayed or stale "delivered" never overwrites a "bounced"/"complained".
STATUS_RANK = {
    EmailStatus.QUEUED.value: 0,
    EmailStatus.SENT.value: 1,
    EmailStatus.DELIVERED.value: 2,
    EmailStatus.FAILED.value: 3,
    EmailStatus.BOUNCED.value: 3,
    EmailStatus.COMPLAINED.value: 3,
    EmailStatus.SKIPPED.value: 3,
}

PERMANENT = "permanent: "  # email_log.error prefix for messages the provider will never accept


def _reason(e: ExternalServiceError) -> str:
    """Log-safe failure summary: provider error name and HTTP status, never message text or addresses."""
    details = e.details if isinstance(e.details, dict) else {}
    return f"{e.code}/{details.get('status') or details.get('error', '-')}"


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
        if record and (record.error or "").startswith(PERMANENT):
            # Rejected for good earlier; a handler retried for a sibling send must not try again (and a
            # 409 replay on the re-attempt must not be mistaken for an accepted send).
            return EmailStatus.FAILED
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
        except PermanentEmailError as e:
            if e.code == "invalid_idempotent_request":
                # An earlier attempt with this key was accepted, but we never recorded it (timeout or
                # crash) and the re-rendered content differs. It was sent; sending again would duplicate.
                record.status = EmailStatus.SENT.value
                record.error = "accepted by an earlier attempt; message id unknown"
                await self._session.commit()
                log.warning("email %s: idempotent replay, treating as sent (template=%s)", record.id, template)
                return EmailStatus.SENT
            record.status = EmailStatus.FAILED.value
            record.error = f"{PERMANENT}{e.message}: {e.details}"[:1000]
            await self._session.commit()
            # Not raised: the outbox would only retry a message that can never be accepted.
            log.error("email %s rejected permanently (template=%s error=%s)", record.id, template, _reason(e))
            return EmailStatus.FAILED
        except ExternalServiceError as e:
            record.status = EmailStatus.FAILED.value
            record.error = f"{e.message}: {e.details}"[:1000]
            await self._session.commit()
            log.warning("email %s failed, will retry (template=%s error=%s)", record.id, template, _reason(e))
            raise
        record.status = EmailStatus.SENT.value
        record.provider_message_id = message_id
        record.error = None
        await self._session.commit()
        log.info("email %s accepted by provider (template=%s message_id=%s)", record.id, template, message_id)
        return EmailStatus.SENT

    async def apply_provider_event(self, event_type: str, data: dict) -> None:
        mapping = RESEND_EVENTS.get(event_type)
        if mapping is None:
            return
        status, suppress = mapping
        message_id = data.get("email_id")
        if isinstance(message_id, str) and message_id:
            record = (
                await self._session.execute(select(EmailLog).where(EmailLog.provider_message_id == message_id))
            ).scalar_one_or_none()
            if record and STATUS_RANK[status.value] > STATUS_RANK.get(record.status, 0):
                record.status = status.value
        recipients = data.get("to")
        if suppress and isinstance(recipients, list):
            for address in recipients:
                if not isinstance(address, str) or "@" not in address:
                    continue
                await self._session.execute(
                    insert(EmailSuppression)
                    .values(email=address.lower(), reason=status.value, created_at=self._clock.now())
                    .on_conflict_do_nothing()
                )
        await self._session.commit()
