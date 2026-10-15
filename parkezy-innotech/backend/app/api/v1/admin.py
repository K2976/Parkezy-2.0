import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, ContainerDep, RulesDep, ServicesDep, page_limit
from app.api.presenters import admin_user_detail, admin_user_out, dispute_out, payout_out, user_out
from app.domain.enums import DisputeStatus, PayoutStatus, UserStatus
from app.schemas.common import Page
from app.schemas.misc import DisputeOut, DisputeReview, OutboxEventOut, QueueStatsOut, SettingOut, SettingsPatch
from app.schemas.payouts import MarkPaidIn, PayoutOut, RejectPayoutIn
from app.schemas.users import AdminUserDetail, AdminUserOut, SuspendRequest, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings", response_model=list[SettingOut])
async def list_settings(_: AdminUser, services: ServicesDep) -> list[SettingOut]:
    return [SettingOut.model_validate(s) for s in await services.settings().list_all()]


@router.patch("/settings", response_model=list[SettingOut])
async def update_settings(body: SettingsPatch, _: AdminUser, services: ServicesDep) -> list[SettingOut]:
    settings = services.settings()
    await settings.update(body.changes)
    return [SettingOut.model_validate(s) for s in await settings.list_all()]


@router.post("/users/{user_id}/commercial-host", response_model=UserOut)
async def grant_commercial(user_id: uuid.UUID, _: AdminUser, services: ServicesDep) -> UserOut:
    return user_out(await services.users().grant_commercial_host(user_id))


@router.get("/disputes", response_model=list[DisputeOut])
async def list_disputes(
    _: AdminUser,
    services: ServicesDep,
    rules: RulesDep,
    c: ContainerDep,
    status: DisputeStatus | None = None,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> list[DisputeOut]:
    disputes = await services.disputes().list_for_review(status, page_limit(rules, limit))
    return [dispute_out(d, c.storage) for d in disputes]


@router.patch("/disputes/{dispute_id}", response_model=DisputeOut)
async def review_dispute(
    dispute_id: uuid.UUID, body: DisputeReview, admin: AdminUser, services: ServicesDep, c: ContainerDep
) -> DisputeOut:
    dispute = await services.disputes().review(admin, dispute_id, body.status, body.resolution)
    return dispute_out(dispute, c.storage)


@router.get("/outbox/stats", response_model=QueueStatsOut)
async def outbox_stats(_: AdminUser, services: ServicesDep) -> QueueStatsOut:
    return QueueStatsOut(**await services.ops().queue_stats())


@router.get("/outbox/dead-letters", response_model=list[OutboxEventOut])
async def dead_letters(
    _: AdminUser, services: ServicesDep, rules: RulesDep, limit: Annotated[int | None, Query(gt=0)] = None
) -> list[OutboxEventOut]:
    return [OutboxEventOut.model_validate(e) for e in await services.ops().dead_letters(page_limit(rules, limit))]


@router.post("/outbox/{event_id}/retry", response_model=OutboxEventOut)
async def retry_event(event_id: uuid.UUID, _: AdminUser, services: ServicesDep, c: ContainerDep) -> OutboxEventOut:
    event = await services.ops().retry(event_id)
    await asyncio.to_thread(c.jobs.enqueue, "process_outbox")
    return OutboxEventOut.model_validate(event)


# ------------------------------------------------------------------ users
@router.get("/users", response_model=Page[AdminUserOut])
async def list_users(
    _: AdminUser,
    services: ServicesDep,
    rules: RulesDep,
    q: Annotated[str | None, Query(max_length=120)] = None,
    status: UserStatus | None = None,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> Page[AdminUserOut]:
    users, next_cursor = await services.admin_users().search(
        q=q, status=status, cursor=cursor, limit=page_limit(rules, limit)
    )
    return Page[AdminUserOut](items=[admin_user_out(u) for u in users], next_cursor=next_cursor)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user(user_id: uuid.UUID, _: AdminUser, services: ServicesDep) -> AdminUserDetail:
    admin_users = services.admin_users()
    user = await admin_users.get(user_id)
    return admin_user_detail(user, await admin_users.counts(user))


@router.post("/users/{user_id}/suspend", response_model=AdminUserDetail)
async def suspend_user(
    user_id: uuid.UUID, body: SuspendRequest, admin: AdminUser, services: ServicesDep
) -> AdminUserDetail:
    admin_users = services.admin_users()
    user = await admin_users.suspend(admin, user_id, body.reason)
    return admin_user_detail(user, await admin_users.counts(user))


@router.post("/users/{user_id}/unsuspend", response_model=AdminUserDetail)
async def unsuspend_user(user_id: uuid.UUID, _: AdminUser, services: ServicesDep) -> AdminUserDetail:
    admin_users = services.admin_users()
    user = await admin_users.unsuspend(user_id)
    return admin_user_detail(user, await admin_users.counts(user))


# ------------------------------------------------------------------ payouts
@router.get("/payouts", response_model=Page[PayoutOut])
async def list_payouts(
    _: AdminUser,
    services: ServicesDep,
    rules: RulesDep,
    status: PayoutStatus | None = None,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> Page[PayoutOut]:
    items, next_cursor = await services.payouts().list_all(status=status, cursor=cursor, limit=page_limit(rules, limit))
    return Page[PayoutOut](items=[payout_out(p) for p in items], next_cursor=next_cursor)


@router.post("/payouts/{payout_id}/mark-paid", response_model=PayoutOut)
async def mark_payout_paid(
    payout_id: uuid.UUID, body: MarkPaidIn, admin: AdminUser, services: ServicesDep
) -> PayoutOut:
    return payout_out(await services.payouts().mark_paid(admin, payout_id, body.reference))


@router.post("/payouts/{payout_id}/reject", response_model=PayoutOut)
async def reject_payout(
    payout_id: uuid.UUID, body: RejectPayoutIn, admin: AdminUser, services: ServicesDep
) -> PayoutOut:
    return payout_out(await services.payouts().reject(admin, payout_id, body.reason))
