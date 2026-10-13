import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import ExternalServiceError
from app.db.models import Notification, NotificationPreference, PushToken, User
from app.domain.enums import NOTIFICATION_CATEGORY, NotificationCategory, NotificationChannel
from app.integrations.push import PushMessage, PushSender
from app.services.email_service import EmailService

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSpec:
    template: str
    context: dict


class NotificationService:
    def __init__(self, session: AsyncSession, clock: Clock, push: PushSender, email: EmailService | None) -> None:
        self._session = session
        self._clock = clock
        self._push = push
        self._email = email

    # ------------------------------------------------------------ inbox (API)
    async def list_for(
        self, user: User, *, limit: int, before: uuid.UUID | None, unread_only: bool
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        if before:
            anchor = await self._session.get(Notification, before)
            if anchor and anchor.user_id == user.id:
                query = query.where(Notification.created_at < anchor.created_at)
        return list(
            (await self._session.execute(query.order_by(Notification.created_at.desc()).limit(limit))).scalars()
        )

    async def unread_count(self, user: User) -> int:
        return int(
            await self._session.scalar(
                select(func.count()).where(Notification.user_id == user.id, Notification.read_at.is_(None))
            )
            or 0
        )

    async def mark_read(self, user: User, ids: list[uuid.UUID] | None) -> None:
        query = update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
        if ids is not None:
            query = query.where(Notification.id.in_(ids))
        await self._session.execute(query.values(read_at=self._clock.now()))
        await self._session.commit()

    # ------------------------------------------------------------ preferences
    async def preferences(self, user: User) -> dict[str, dict[str, bool]]:
        """Full channel x category matrix; anything not stored is enabled."""
        rows = (
            await self._session.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
        ).scalars()
        stored = {(r.channel, r.category): r.enabled for r in rows}
        return {
            ch.value: {cat.value: stored.get((ch.value, cat.value), True) for cat in NotificationCategory}
            for ch in NotificationChannel
        }

    async def set_preferences(self, user: User, changes: dict[str, dict[str, bool]]) -> dict[str, dict[str, bool]]:
        now = self._clock.now()
        for channel, categories in changes.items():
            for category, enabled in categories.items():
                stmt = insert(NotificationPreference).values(
                    user_id=user.id, channel=channel, category=category, enabled=enabled, updated_at=now
                )
                await self._session.execute(
                    stmt.on_conflict_do_update(
                        index_elements=["user_id", "channel", "category"],
                        set_={"enabled": stmt.excluded.enabled, "updated_at": now},
                    )
                )
        await self._session.commit()
        return await self.preferences(user)

    async def _allowed(self, user: User, channel: NotificationChannel, type_: str) -> bool:
        category = NOTIFICATION_CATEGORY.get(type_)
        if category is None:
            return True
        enabled = await self._session.scalar(
            select(NotificationPreference.enabled).where(
                NotificationPreference.user_id == user.id,
                NotificationPreference.channel == channel.value,
                NotificationPreference.category == category.value,
            )
        )
        return enabled is not False

    # ------------------------------------------------------------ delivery (worker)
    async def deliver(
        self,
        user: User,
        *,
        type_: str,
        title: str,
        body: str,
        data: dict,
        dedupe_key: str,
        email: EmailSpec | None = None,
        in_app: bool = True,
    ) -> None:
        # Retries (e.g. after an email failure) must not duplicate the inbox entry or the push.
        already = await self._session.scalar(
            select(func.count()).where(
                Notification.user_id == user.id, Notification.data["dedupe_key"].astext == dedupe_key
            )
        )
        if not already:
            if in_app:
                self._session.add(
                    Notification(
                        user_id=user.id,
                        type=type_,
                        title=title,
                        body=body,
                        data=data | {"dedupe_key": dedupe_key},
                        created_at=self._clock.now(),
                    )
                )
                await self._session.commit()
            if await self._allowed(user, NotificationChannel.PUSH, type_):
                await self._send_push(user, title, body, data)
        if (
            email
            and self._email
            and user.status == "active"
            and await self._allowed(user, NotificationChannel.EMAIL, type_)
        ):
            await self._email.send(
                to=user.email, template=email.template, context=email.context, dedupe_key=dedupe_key, user_id=user.id
            )

    async def _send_push(self, user: User, title: str, body: str, data: dict) -> None:
        tokens = list(
            (await self._session.execute(select(PushToken.token).where(PushToken.user_id == user.id))).scalars()
        )
        if not tokens:
            return
        try:
            invalid = await self._push.send(PushMessage(tokens=tokens, title=title, body=body, data=data))
        except ExternalServiceError:
            log.warning("push delivery failed for user %s", user.id, exc_info=True)
            return  # push is best-effort; the in-app notification is the record
        if invalid:
            await self._session.execute(delete(PushToken).where(PushToken.token.in_(invalid)))
            await self._session.commit()
