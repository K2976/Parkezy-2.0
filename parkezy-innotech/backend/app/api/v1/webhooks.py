import orjson
from fastapi import APIRouter, Request, status

from app.api.deps import ContainerDep, ServicesDep
from app.core.errors import Unauthorized, ValidationFailed
from app.integrations.webhooks import verify_svix_signature
from app.schemas.common import Message

router = APIRouter(prefix="/webhooks", tags=["webhooks"], include_in_schema=False)


def _json(body: bytes) -> dict:
    try:
        return orjson.loads(body)
    except orjson.JSONDecodeError as e:
        raise ValidationFailed("Invalid JSON body") from e


@router.post("/razorpay", response_model=Message, status_code=status.HTTP_200_OK)
async def razorpay(request: Request, services: ServicesDep) -> Message:
    body = await request.body()
    event = _json(body)
    event_id = request.headers.get("x-razorpay-event-id") or f"{event.get('event')}:{event.get('created_at')}"
    await services.payments().handle_webhook(
        body=body, signature=request.headers.get("x-razorpay-signature", ""), event_id=event_id, event=event
    )
    return Message(message="ok")


@router.post("/resend", response_model=Message)
async def resend(request: Request, services: ServicesDep, c: ContainerDep) -> Message:
    secret = c.settings.resend_webhook_secret
    if secret is None:
        raise Unauthorized("Resend webhooks are not configured", code="webhook_not_configured")
    body = await request.body()
    if not verify_svix_signature(
        secret=secret.get_secret_value(),
        msg_id=request.headers.get("svix-id", ""),
        timestamp=request.headers.get("svix-timestamp", ""),
        signature_header=request.headers.get("svix-signature", ""),
        body=body,
        now=c.clock.now(),
    ):
        raise Unauthorized("Invalid webhook signature", code="webhook_signature_invalid")
    event = _json(body)
    data = event.get("data") if isinstance(event, dict) else None
    if not isinstance(data, dict):
        raise ValidationFailed("Invalid webhook payload")
    # Processing is idempotent (statuses only move forward, suppressions are upserts), so Svix's
    # at-least-once redeliveries need no separate dedupe table.
    await services.email().apply_provider_event(str(event.get("type", "")), data)
    return Message(message="ok")
