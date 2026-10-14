from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, OptionalUser, RateLimit, RulesDep, ServicesDep, page_limit
from app.core.errors import ValidationFailed
from app.db.models import SupportTicket
from app.schemas.misc import SupportCreate, SupportTicketOut

router = APIRouter(prefix="/support", tags=["support"])
# Open to signed-out users, so it shares the strict per-IP bucket used by sign-in.
support_limit = Depends(RateLimit("support", "rate_limit_auth_per_window"))


def _out(t: SupportTicket) -> SupportTicketOut:
    return SupportTicketOut(
        id=t.id,
        reference=str(t.id)[-8:].upper(),
        category=t.category,
        subject=t.subject,
        status=t.status,
        created_at=t.created_at,
    )


@router.post("", response_model=SupportTicketOut, status_code=status.HTTP_201_CREATED, dependencies=[support_limit])
async def create_ticket(body: SupportCreate, user: OptionalUser, services: ServicesDep) -> SupportTicketOut:
    if user is None and body.email is None:
        raise ValidationFailed("Tell us an email address to reply to", code="email_required")
    ticket = await services.support().create(
        user,
        email=body.email,
        name=body.name,
        category=body.category,
        subject=body.subject,
        message=body.message,
        booking_id=body.booking_id,
    )
    return _out(ticket)


@router.get("/tickets", response_model=list[SupportTicketOut])
async def my_tickets(
    user: CurrentUser, services: ServicesDep, rules: RulesDep, limit: Annotated[int | None, Query(gt=0)] = None
) -> list[SupportTicketOut]:
    return [_out(t) for t in await services.support().list_mine(user, page_limit(rules, limit))]
