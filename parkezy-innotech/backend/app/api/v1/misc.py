"""Uploads, payments, notifications and disputes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import ContainerDep, CurrentUser, RulesDep, ServicesDep, page_limit
from app.api.presenters import dispute_out
from app.schemas.common import Message
from app.schemas.misc import (
    DisputeCreate,
    DisputeOut,
    MarkReadRequest,
    NotificationList,
    NotificationOut,
    PaymentConfirmRequest,
    PaymentOrderOut,
    UploadCompleteOut,
    UploadOut,
    UploadRequest,
)

router = APIRouter()


# ------------------------------------------------------------------ uploads
@router.post("/uploads", response_model=UploadOut, status_code=status.HTTP_201_CREATED, tags=["uploads"])
async def create_upload(body: UploadRequest, user: CurrentUser, services: ServicesDep, c: ContainerDep) -> UploadOut:
    upload, presigned = await services.uploads().create(user, body.purpose, body.content_type)
    return UploadOut(
        id=upload.id,
        upload_url=presigned.url,
        method=presigned.method,
        headers=presigned.headers,
        expires_in=presigned.expires_in,
        max_bytes=c.settings.upload_max_bytes,
    )


@router.post("/uploads/{upload_id}/complete", response_model=UploadCompleteOut, tags=["uploads"])
async def complete_upload(upload_id: uuid.UUID, user: CurrentUser, services: ServicesDep) -> UploadCompleteOut:
    upload = await services.uploads().complete(user, upload_id)
    return UploadCompleteOut(id=upload.id, status=upload.status, size_bytes=upload.size_bytes)


# ------------------------------------------------------------------ payments
@router.post("/bookings/{booking_id}/payment", response_model=PaymentOrderOut, tags=["payments"])
async def create_payment(
    booking_id: uuid.UUID, user: CurrentUser, services: ServicesDep, c: ContainerDep
) -> PaymentOrderOut:
    order, booking = await services.payments().create_order(user, booking_id)
    return PaymentOrderOut(
        provider=order.provider,
        order_id=order.order_id,
        amount_minor=order.amount_minor,
        currency=order.currency,
        key_id=order.public_key,
        booking_id=booking.id,
        description=f"{c.settings.app_name} booking",
        prefill_email=user.email,
        prefill_phone=user.phone,
    )


@router.post("/bookings/{booking_id}/payment/confirm", response_model=Message, tags=["payments"])
async def confirm_payment(
    booking_id: uuid.UUID, body: PaymentConfirmRequest, user: CurrentUser, services: ServicesDep
) -> Message:
    booking = await services.payments().confirm_checkout(
        user, booking_id, order_id=body.order_id, payment_id=body.payment_id, signature=body.signature
    )
    return Message(message=f"Payment received; booking is {booking.status}")


# ------------------------------------------------------------------ notifications
@router.get("/notifications", response_model=NotificationList, tags=["notifications"])
async def notifications(
    user: CurrentUser,
    services: ServicesDep,
    rules: RulesDep,
    before: uuid.UUID | None = None,
    unread_only: bool = False,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> NotificationList:
    service = services.notifications()
    items = await service.list_for(user, limit=page_limit(rules, limit), before=before, unread_only=unread_only)
    return NotificationList(
        items=[NotificationOut.model_validate(n) for n in items], unread_count=await service.unread_count(user)
    )


@router.post("/notifications/read", status_code=status.HTTP_204_NO_CONTENT, tags=["notifications"])
async def mark_read(body: MarkReadRequest, user: CurrentUser, services: ServicesDep) -> None:
    await services.notifications().mark_read(user, body.ids)


# ------------------------------------------------------------------ disputes
@router.post("/disputes", response_model=DisputeOut, status_code=status.HTTP_201_CREATED, tags=["disputes"])
async def create_dispute(
    body: DisputeCreate, user: CurrentUser, services: ServicesDep, rules: RulesDep, c: ContainerDep
) -> DisputeOut:
    dispute = await services.disputes().create(
        user,
        booking_id=body.booking_id,
        reason=body.reason,
        description=body.description,
        evidence_upload_ids=body.evidence_upload_ids,
        rules=rules,
    )
    return dispute_out(dispute, c.storage)


@router.get("/disputes", response_model=list[DisputeOut], tags=["disputes"])
async def my_disputes(user: CurrentUser, services: ServicesDep, c: ContainerDep) -> list[DisputeOut]:
    return [dispute_out(d, c.storage) for d in await services.disputes().list_mine(user)]
