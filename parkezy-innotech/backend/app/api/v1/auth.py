from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import ContainerDep, CurrentUser, RateLimit, ServicesDep, client_ip
from app.api.presenters import user_out
from app.core.errors import Unauthorized
from app.core.security import sha256_hex
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
    SocialSignInRequest,
    TokenOut,
    UserOut,
)
from app.services.auth_service import TokenPair
from app.services.login_protection import LoginContext

router = APIRouter(prefix="/auth", tags=["auth"])
auth_limit = Depends(RateLimit("auth", "rate_limit_auth_per_window"))
# Refresh has its own, looser bucket: apps refresh silently in the background, and many users can share
# one IP (campus Wi-Fi, carrier NAT). Sharing the strict login bucket would log real users out.
# Refresh tokens are long random secrets, so guessing them is not what this limit protects against.
refresh_limit = Depends(RateLimit("refresh", "rate_limit_default_per_window"))


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
async def login(body: LoginRequest, request: Request, services: ServicesDep, c: ContainerDep) -> AuthOut:
    # Per-account limit on top of the per-IP one, so guesses spread over many IPs still hit a wall.
    await c.rate_limiter.hit(
        "login_account",
        sha256_hex(body.email.strip().lower()),
        c.settings.rate_limit_auth_per_window,
        c.settings.rate_limit_window_seconds,
    )
    guard = c.login_guard
    assert guard is not None
    ctx = LoginContext.build(
        ip=client_ip(request, c),
        email=body.email,
        device_header=request.headers.get("x-device-id"),
        user_agent=request.headers.get("user-agent"),
    )
    # Cheap risk check first: throttled or unchallenged requests never reach the argon2 verify.
    await guard.check(ctx, body.challenge_token)
    try:
        user, pair = await services.auth().login(
            email=body.email, password=body.password, user_agent=request.headers.get("user-agent")
        )
    except Unauthorized:
        await guard.record_failure(ctx)
        raise
    await guard.record_success(ctx)
    return AuthOut(user=user_out(user), tokens=_tokens(pair))


@router.post("/social", response_model=AuthOut, status_code=status.HTTP_201_CREATED, dependencies=[auth_limit])
async def social_sign_in(
    body: SocialSignInRequest, request: Request, response: Response, services: ServicesDep, c: ContainerDep
) -> AuthOut:
    """Sign in with Google or Apple. 201 when a new account was created, 200 otherwise."""
    user, pair, created = await services.auth().social_sign_in(
        c.identity_verifier,
        provider=body.provider.value,
        id_token=body.id_token,
        nonce=body.nonce,
        full_name=body.full_name,
        email=body.email,
        user_agent=request.headers.get("user-agent"),
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return AuthOut(user=user_out(user), tokens=_tokens(pair))


@router.post("/refresh", response_model=TokenOut, dependencies=[refresh_limit])
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


async def _email_limit(c: ContainerDep, bucket: str, identity: str) -> None:
    s = c.settings
    await c.rate_limiter.hit(bucket, identity, s.rate_limit_email_per_window, s.rate_limit_email_window_seconds)


@router.post("/resend-verification", response_model=Message, dependencies=[auth_limit])
async def resend_verification(user: CurrentUser, services: ServicesDep, c: ContainerDep) -> Message:
    await _email_limit(c, "verify_email_account", str(user.id))
    await services.auth().resend_verification(user)
    return Message(message="A new code is on its way")


@router.post("/forgot-password", response_model=Message, dependencies=[auth_limit])
async def forgot_password(body: EmailRequest, services: ServicesDep, c: ContainerDep) -> Message:
    # Keyed on the address asked for, before any lookup, so it limits unknown and real accounts alike
    # (no enumeration) and holds even when requests rotate through many IPs.
    await _email_limit(c, "reset_email_account", sha256_hex(body.email.strip().lower()))
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
