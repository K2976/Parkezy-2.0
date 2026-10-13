from fastapi import APIRouter, status

from app.api.deps import CurrentUser, ServicesDep
from app.api.presenters import user_out
from app.schemas.common import Message
from app.schemas.users import NotificationPreferences, ProfileUpdate, PushTokenRequest, UserOut

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return user_out(user)


@router.patch("", response_model=UserOut)
async def update_me(body: ProfileUpdate, user: CurrentUser, services: ServicesDep) -> UserOut:
    return user_out(await services.users().update_profile(user, full_name=body.full_name, phone=body.phone))


@router.post("/become-host", response_model=UserOut)
async def become_host(user: CurrentUser, services: ServicesDep) -> UserOut:
    return user_out(await services.users().become_host(user))


@router.post("/push-tokens", status_code=status.HTTP_204_NO_CONTENT)
async def add_push_token(body: PushTokenRequest, user: CurrentUser, services: ServicesDep) -> None:
    await services.users().register_push_token(user, body.token, body.platform)


@router.post("/push-tokens/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_push_token(body: PushTokenRequest, user: CurrentUser, services: ServicesDep) -> None:
    await services.users().remove_push_token(user, body.token)


@router.delete("", response_model=Message)
async def delete_account(user: CurrentUser, services: ServicesDep) -> Message:
    await services.users().delete_account(user)
    return Message(message="Your account has been deleted")


@router.get("/notification-preferences", response_model=NotificationPreferences)
async def get_preferences(user: CurrentUser, services: ServicesDep) -> NotificationPreferences:
    return NotificationPreferences.model_validate(await services.notifications().preferences(user))


@router.put("/notification-preferences", response_model=NotificationPreferences)
async def set_preferences(
    body: NotificationPreferences, user: CurrentUser, services: ServicesDep
) -> NotificationPreferences:
    changes = {channel: {k.value: v for k, v in cats.items()} for channel, cats in body.model_dump().items() if cats}
    return NotificationPreferences.model_validate(await services.notifications().set_preferences(user, changes))
