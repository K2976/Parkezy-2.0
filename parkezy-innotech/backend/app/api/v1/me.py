import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ContainerDep, CurrentUser, RateLimit, RulesDep, ServicesDep, page_limit
from app.api.presenters import favorite_out, user_out
from app.schemas.common import Message, Page
from app.schemas.listings import FavoriteOut
from app.schemas.users import DeleteAccountRequest, NotificationPreferences, ProfileUpdate, PushTokenRequest, UserOut

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


# Requires the password again, under the strict sign-in limit so it cannot be used to guess passwords.
@router.delete("", response_model=Message, dependencies=[Depends(RateLimit("auth", "rate_limit_auth_per_window"))])
async def delete_account(body: DeleteAccountRequest, user: CurrentUser, services: ServicesDep) -> Message:
    await services.users().delete_account(user, body.password)
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


# ------------------------------------------------------------------ favourites
@router.get("/favorites", response_model=Page[FavoriteOut])
async def favorites(
    user: CurrentUser,
    services: ServicesDep,
    rules: RulesDep,
    c: ContainerDep,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(gt=0)] = None,
) -> Page[FavoriteOut]:
    items, next_cursor = await services.favorites().list(user, cursor=cursor, limit=page_limit(rules, limit))
    return Page[FavoriteOut](
        items=[favorite_out(listing, fav, cover, c.storage) for listing, fav, cover in items], next_cursor=next_cursor
    )


@router.put("/favorites/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def save_favorite(listing_id: uuid.UUID, user: CurrentUser, services: ServicesDep) -> None:
    await services.favorites().save(user, listing_id)


@router.delete("/favorites/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(listing_id: uuid.UUID, user: CurrentUser, services: ServicesDep) -> None:
    await services.favorites().remove(user, listing_id)
