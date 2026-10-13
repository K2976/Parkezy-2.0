import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.models import Booking, Dispute, User
from app.domain.enums import BookingStatus, DisputeReason, DisputeStatus, UploadPurpose
from app.domain.rules import PlatformRules
from app.services.outbox import Event, Outbox
from app.services.upload_service import UploadService

DISPUTABLE = {
    BookingStatus.CONFIRMED.value,
    BookingStatus.CHECKED_IN.value,
    BookingStatus.COMPLETED.value,
    BookingStatus.EXPIRED.value,
    BookingStatus.CANCELLED.value,
}


class DisputeService:
    def __init__(self, session: AsyncSession, clock: Clock, uploads: UploadService) -> None:
        self._session = session
        self._clock = clock
        self._uploads = uploads
        self._outbox = Outbox(session, clock)

    async def create(
        self,
        user: User,
        *,
        booking_id: uuid.UUID,
        reason: DisputeReason,
        description: str,
        evidence_upload_ids: list[uuid.UUID],
        rules: PlatformRules,
    ) -> Dispute:
        if len(evidence_upload_ids) > rules.max_dispute_photos:
            raise ValidationFailed("Too many photos", details={"max": rules.max_dispute_photos})
        booking = await self._session.get(Booking, booking_id)
        if booking is None or user.id not in (booking.driver_id, booking.host_id):
            raise NotFound("Booking not found")
        if booking.status not in DISPUTABLE:
            raise Conflict("This booking cannot be disputed", code="not_disputable")
        open_existing = await self._session.scalar(
            select(Dispute.id).where(
                Dispute.booking_id == booking.id,
                Dispute.reporter_id == user.id,
                Dispute.status.in_([DisputeStatus.OPEN.value, DisputeStatus.IN_REVIEW.value]),
            )
        )
        if open_existing:
            raise Conflict("You already have an open report for this booking", code="dispute_exists")
        evidence = await self._uploads.require_uploaded(user, evidence_upload_ids, UploadPurpose.DISPUTE_EVIDENCE)
        dispute = Dispute(
            booking_id=booking.id,
            reporter_id=user.id,
            reason=reason.value,
            description=description,
            evidence_keys=[u.storage_key for u in evidence],
            status=DisputeStatus.OPEN.value,
        )
        self._session.add(dispute)
        await self._session.flush()
        self._outbox.add(Event.DISPUTE_CREATED, {"dispute_id": str(dispute.id)})
        await self._session.commit()
        return dispute

    async def list_mine(self, user: User) -> list[Dispute]:
        return list(
            (
                await self._session.execute(
                    select(Dispute).where(Dispute.reporter_id == user.id).order_by(Dispute.created_at.desc())
                )
            ).scalars()
        )

    async def list_for_review(self, status: DisputeStatus | None, limit: int) -> list[Dispute]:
        query = select(Dispute)
        if status:
            query = query.where(Dispute.status == status.value)
        return list((await self._session.execute(query.order_by(Dispute.created_at).limit(limit))).scalars())

    async def review(
        self, admin: User, dispute_id: uuid.UUID, status: DisputeStatus, resolution: str | None
    ) -> Dispute:
        dispute = await self._session.get(Dispute, dispute_id, with_for_update=True)
        if dispute is None:
            raise NotFound("Dispute not found")
        if dispute.status in (DisputeStatus.RESOLVED.value, DisputeStatus.REJECTED.value):
            raise Conflict("Dispute is already closed", code="dispute_closed")
        dispute.status = status.value
        dispute.resolution = resolution
        if status in (DisputeStatus.RESOLVED, DisputeStatus.REJECTED):
            dispute.resolved_by = admin.id
        self._outbox.add(Event.DISPUTE_UPDATED, {"dispute_id": str(dispute.id)})
        await self._session.commit()
        return dispute
