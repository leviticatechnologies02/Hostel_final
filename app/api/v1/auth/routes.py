from fastapi import APIRouter, Body, Request, Response, HTTPException, status

from app.config import get_settings
from app.dependencies import DBSession
from app.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    OTPVerifyRequest,
    RefreshTokenRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    TokenResponse,
    VisitorRegisterResponse,
    VisitorRegisterRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()
settings = get_settings()


def _set_refresh_cookie(response: Response, *, refresh_token: str) -> None:
    # Cookie security: secure cookies require HTTPS (production).
    secure = settings.app_env == "production"
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
        secure=secure,
        path=settings.refresh_cookie_path,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
    )


@router.post("/register/visitor", response_model=VisitorRegisterResponse, status_code=201)
async def register_visitor(payload: VisitorRegisterRequest, db: DBSession):
    """
    Register a new visitor account.

    Creates a user with role `visitor`. After registration, an OTP is sent
    to verify the email/phone before the account is fully active.
    """
    return await AuthService(db).register_visitor(payload)


@router.post("/register", response_model=VisitorRegisterResponse, status_code=201)
async def register(payload: VisitorRegisterRequest, db: DBSession):
    """Spec alias for registering a visitor account."""
    return await AuthService(db).register_visitor(payload)


@router.post("/register/verify-otp", response_model=VisitorRegisterResponse)
async def verify_registration_otp(payload: OTPVerifyRequest, db: DBSession):
    """
    Verify OTP sent during registration.

    Marks the user's email and phone as verified and activates the visitor.
    """
    return await AuthService(db).verify_registration_otp(payload)


@router.post("/verify-otp", response_model=VisitorRegisterResponse) 
async def verify_otp(payload: OTPVerifyRequest, db: DBSession):
    """Spec alias for verifying registration OTP."""
    return await AuthService(db).verify_registration_otp(payload)


@router.post("/register/resend-otp")
async def resend_registration_otp(payload: ResendOTPRequest, db: DBSession):
    """
    Resend registration OTP.

    Use this if the original OTP expired or was not received.
    Requires `user_id` from the registration response.
    """
    return await AuthService(db).resend_registration_otp(payload.user_id)


@router.post("/login", response_model=AccessTokenResponse)
async def login(payload: LoginRequest, response: Response, db: DBSession):
    """
    Login with email or phone + password.

    Returns an access token and sets an httpOnly refresh cookie.
    """
    token_pair = await AuthService(db).login(payload)
    _set_refresh_cookie(response, refresh_token=token_pair.refresh_token)
    return AccessTokenResponse(
        user_id=token_pair.user_id,
        access_token=token_pair.access_token,
        token_type=token_pair.token_type,
        role=token_pair.role,
        hostel_ids=token_pair.hostel_ids,
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(request: Request, response: Response, db: DBSession):
    """Spec refresh: rotate httpOnly refresh cookie and return a new access token."""
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing.")

    token_pair = await AuthService(db).refresh_tokens(RefreshTokenRequest(refresh_token=refresh_token))
    _set_refresh_cookie(response, refresh_token=token_pair.refresh_token)
    return AccessTokenResponse(
        user_id=token_pair.user_id,
        access_token=token_pair.access_token,
        token_type=token_pair.token_type,
        role=token_pair.role,
        hostel_ids=token_pair.hostel_ids,
        expires_in=token_pair.expires_in,
    )
    
# Legacy endpoint (body-based). Kept for backward compatibility.
@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest, db: DBSession):
    """
    Refresh access token using a valid refresh token (body-based legacy).
    """
    return await AuthService(db).refresh_tokens(payload)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: DBSession,
    payload: LogoutRequest | None = Body(default=None),
):
    """
    Logout — revoke the refresh token and clear the httpOnly cookie.
    """
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token and payload is not None:
        # Backward compatibility: allow token in request body.
        refresh_token = payload.refresh_token

    if refresh_token:
        await AuthService(db).logout(LogoutRequest(refresh_token=refresh_token))

    _clear_refresh_cookie(response)
    return {"message": "Logged out."}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: DBSession):
    """
    Initiate password reset.

    Sends a 6-digit OTP to the registered email (or phone).
    """
    return await AuthService(db).forgot_password(payload.email_or_phone)


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: DBSession):
    """
    Reset password using OTP.

    Requires the `user_id` and `otp_code` from the forgot-password flow,
    plus the new password. OTP is single-use and expires in 10 minutes.
    """
    return await AuthService(db).reset_password(payload)
