from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CurrentUser, RateLimit, ServicesDep
from app.api.presenters import user_out
from app.schemas.common import Message
from app.schemas.users import (
    AuthOut,
    ChangePasswordRequest,
    CodeRequest,
    EmailRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenOut,
    UserOut,
)
from app.services.auth_service import TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])
auth_limit = Depends(RateLimit("auth", "rate_limit_auth_per_window"))


def _tokens(pair: TokenPair) -> TokenOut:
    return TokenOut(
        access_token=pair.access_token,
        access_expires_at=pair.access_expires_at,
        refresh_token=pair.refresh_token,
        refresh_expires_at=pair.refresh_expires_at,
    )


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED, dependencies=[auth_limit])
async def register(body: RegisterRequest, request: Request, services: ServicesDep) -> AuthOut:
    auth = services.auth()
    user = await auth.register(email=body.email, password=body.password, full_name=body.full_name, phone=body.phone)
    pair = await auth.issue_for(user, request.headers.get("user-agent"))
    return AuthOut(user=user_out(user), tokens=_tokens(pair))


@router.post("/login", response_model=AuthOut, dependencies=[auth_limit])
async def login(body: LoginRequest, request: Request, services: ServicesDep) -> AuthOut:
    user, pair = await services.auth().login(
        email=body.email, password=body.password, user_agent=request.headers.get("user-agent")
    )
    return AuthOut(user=user_out(user), tokens=_tokens(pair))


@router.post("/refresh", response_model=TokenOut, dependencies=[auth_limit])
async def refresh(body: RefreshRequest, request: Request, services: ServicesDep) -> TokenOut:
    pair = await services.auth().refresh(refresh_token=body.refresh_token, user_agent=request.headers.get("user-agent"))
    return _tokens(pair)


@router.post("/logout", response_model=Message)
async def logout(body: RefreshRequest, services: ServicesDep) -> Message:
    await services.auth().logout(refresh_token=body.refresh_token)
    return Message(message="Signed out")


@router.post("/verify-email", response_model=UserOut, dependencies=[auth_limit])
async def verify_email(body: CodeRequest, user: CurrentUser, services: ServicesDep) -> UserOut:
    return user_out(await services.auth().verify_email(user, body.code))


@router.post("/resend-verification", response_model=Message, dependencies=[auth_limit])
async def resend_verification(user: CurrentUser, services: ServicesDep) -> Message:
    await services.auth().resend_verification(user)
    return Message(message="A new code is on its way")


@router.post("/forgot-password", response_model=Message, dependencies=[auth_limit])
async def forgot_password(body: EmailRequest, services: ServicesDep) -> Message:
    await services.auth().forgot_password(body.email)
    return Message(message="If that email has an account, a reset code is on its way")


@router.post("/reset-password", response_model=Message, dependencies=[auth_limit])
async def reset_password(body: ResetPasswordRequest, services: ServicesDep) -> Message:
    await services.auth().reset_password(email=body.email, code=body.code, new_password=body.new_password)
    return Message(message="Password updated, please sign in")


@router.post("/change-password", response_model=Message, dependencies=[auth_limit])
async def change_password(body: ChangePasswordRequest, user: CurrentUser, services: ServicesDep) -> Message:
    await services.auth().change_password(user, current_password=body.current_password, new_password=body.new_password)
    return Message(message="Password updated, please sign in again")
