from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    OTPVerifyRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
    VisitorRegisterRequest,
    VisitorRegisterResponse,
)
from app.config import get_settings
from app.services.otp_service import OTPService
from app.models.user import OTPType

settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    async def register_visitor(self, payload: VisitorRegisterRequest) -> VisitorRegisterResponse:
        existing = await self.repository.get_by_email_or_phone(payload.email)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
        existing_phone = await self.repository.get_by_email_or_phone(payload.phone)
        if existing_phone is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered.")

        user = await self.repository.create_visitor(
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            password_hash=hash_password(payload.password),
        )
        await self.session.commit()

        # Send registration OTP
        otp_service = OTPService(self.session)
        otp_code = await otp_service.create_otp(
            user_id=str(user.id),
            otp_type=OTPType.REGISTRATION.value,
        )
        await self.session.commit()
        # Send OTP via Email + SMS simultaneously
        await otp_service.send_otp(user.email, user.phone, otp_code, OTPType.REGISTRATION.value)

        return VisitorRegisterResponse(
            user_id=str(user.id),
            email=user.email,
            phone=user.phone,
            message="Registration successful. Please verify your email with the OTP sent.",
        )

    async def login(self, payload: LoginRequest, device_info: str | None = None, ip_address: str | None = None) -> TokenResponse:
        """
        Login with device tracking.
        
        Args:
            payload: Login credentials
            device_info: User agent or device identifier
            ip_address: Client IP address
        """
        user = await self.repository.get_by_email_or_phone(payload.email_or_phone.strip())
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support."
            )
        
        # Issue tokens with device info
        return await self.issue_tokens(
            user_id=str(user.id),
            device_info=device_info,
            ip_address=ip_address
        )

    async def issue_tokens(self, user_id: str, device_info: str | None = None, ip_address: str | None = None) -> TokenResponse:
        """Issue access and refresh tokens with device tracking."""
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        # Store refresh token with device info
        await self.repository.create_refresh_token(
            user_id=user_id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            device_name=device_info,
            ip_address=ip_address,
        )
        
        # Update last login
        user = await self.repository.get_by_id(user_id)  
        
        await self.session.commit()

        # Fetch hostel_ids for admin/supervisor roles
        hostel_ids: list[str] = []
        role = ""
        if user:
            role = user.role.value if hasattr(user.role, "value") else str(user.role)  
            if role in ("hostel_admin", "supervisor"):
                from sqlalchemy import select
                from app.models.hostel import AdminHostelMapping, SupervisorHostelMapping
                if role == "hostel_admin":
                    result = await self.session.execute(
                        select(AdminHostelMapping.hostel_id).where(AdminHostelMapping.admin_id == user_id)
                    )
                else:
                    result = await self.session.execute(
                        select(SupervisorHostelMapping.hostel_id).where(SupervisorHostelMapping.supervisor_id == user_id)
                    )
                hostel_ids = [str(hid) for hid in result.scalars().all()]

        return TokenResponse(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            role=role,
            hostel_ids=hostel_ids,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def refresh_tokens(self, payload: RefreshTokenRequest) -> TokenResponse:
        refresh_token_hash = hash_token(payload.refresh_token)
        stored = await self.repository.get_refresh_token(refresh_token_hash)
        if stored is None or stored.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
        if stored.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")
        token_payload = decode_token(payload.refresh_token)
        if token_payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
        await self.repository.revoke_refresh_token(refresh_token_hash, datetime.now(UTC))
        return await self.issue_tokens(token_payload["sub"])

    async def logout(self, payload: LogoutRequest) -> dict:
        """
        Logout by revoking refresh token.
        
        This invalidates the refresh token, preventing further token refresh.
        Active access tokens remain valid until they expire (short-lived).
        """
        refresh_token_hash = hash_token(payload.refresh_token)
        revoked = await self.repository.revoke_refresh_token(refresh_token_hash, datetime.now(UTC))
        
        if revoked:
            await self.session.commit()
            return {"message": "Logout successful."}
        else:
            # Token not found or already revoked - still return success (idempotent)
            return {"message": "Logout successful (token already revoked)."}

    async def verify_registration_otp(self, payload: OTPVerifyRequest) -> VisitorRegisterResponse:
        """Verify OTP during registration"""
        otp_service = OTPService(self.session)
        
        # Verify the OTP
        await otp_service.verify_otp(
            user_id=payload.user_id,
            otp_code=payload.otp_code,
            otp_type=OTPType.REGISTRATION.value,
        )
        
        # Mark email/phone as verified
        user = await self.repository.get_by_id(payload.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        
        user.is_email_verified = True
        user.is_phone_verified = True
        # Activate the visitor account only after successful OTP verification.
        user.is_active = True
        await self.session.commit()
        
        return VisitorRegisterResponse(
            user_id=str(user.id),
            email=user.email,
            phone=user.phone,
            message="Email verified successfully.",
        )

    async def resend_registration_otp(self, email_or_phone: str) -> dict:
        """Resend OTP for registration"""
        otp_service = OTPService(self.session)
        
        user = await self.repository.get_by_email_or_phone(email_or_phone)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        
        if user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already verified."
            )
        
        otp_code = await otp_service.resend_otp(
            user_id=str(user.id),
            otp_type=OTPType.REGISTRATION.value,
        )
        
        await self.session.commit()

        # Send OTP via Email + SMS simultaneously
        await otp_service.send_otp(user.email, user.phone, otp_code, OTPType.REGISTRATION.value)
        
        return {
            "message": "OTP resent.",
            "user_id": str(user.id)
        }

    async def forgot_password(self, email_or_phone: str) -> dict:
        """Initiate password reset by sending OTP"""
        otp_service = OTPService(self.session)
        
        user = await self.repository.get_by_email_or_phone(email_or_phone)
        if not user:
            # Don't reveal if user exists (security) — but still return user_id as None
            return {"message": "If this user exists, an OTP has been sent.", "user_id": None}
        
        otp_code = await otp_service.create_otp(
            user_id=str(user.id),
            otp_type=OTPType.PASSWORD_RESET.value,
        )
        
        await self.session.commit()

        # Send OTP via Email + SMS simultaneously
        await otp_service.send_otp(user.email, user.phone, otp_code, OTPType.PASSWORD_RESET.value)
        
        return {
            "message": "Password reset OTP sent.",
            "user_id": str(user.id),
        }

    async def reset_password(self, payload: ResetPasswordRequest) -> dict:
        """Reset password after OTP verification"""
        otp_service = OTPService(self.session)
        
        user = await self.repository.get_by_id(payload.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        
        # Verify the OTP
        await otp_service.verify_otp(
            user_id=payload.user_id,
            otp_code=payload.otp_code,
            otp_type=OTPType.PASSWORD_RESET.value,
        )
        
        # Update password
        user.password_hash = hash_password(payload.new_password)
        await self.session.commit()
        
        return {
            "message": "Password reset successful.",
            "user_id": payload.user_id
        }
    
    async def get_active_sessions(self, user_id: str) -> list[dict]:
        """
        Get all active sessions (refresh tokens) for a user.
        
        Useful for security dashboard - shows where user is logged in.
        """
        sessions = await self.repository.get_active_refresh_tokens(user_id)
        return [
            {
                "id": str(session.id),
                "device_name": session.device_name or "Unknown Device",
                "ip_address": session.ip_address,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "is_current": False  # Frontend can mark current session
            }
            for session in sessions
        ]
    
    async def revoke_session(self, user_id: str, token_id: str) -> dict:
        """
        Revoke a specific session (logout from specific device).
        """
        revoked = await self.repository.revoke_refresh_token_by_id(token_id, datetime.now(UTC))
        if revoked:
            await self.session.commit()
            return {"message": "Session revoked successfully."}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or already revoked."
            )
    
    async def revoke_all_sessions(self, user_id: str, keep_current_token: str | None = None) -> dict:
        """
        Revoke all sessions (logout from all devices).
        
        Optionally keep current session active (useful when changing password).
        
        Args:
            user_id: User ID
            keep_current_token: Optional refresh token to keep active
        """
        count = await self.repository.revoke_all_refresh_tokens(
            user_id=user_id,
            exclude_token_hash=hash_token(keep_current_token) if keep_current_token else None,
            revoked_at=datetime.now(UTC)
        )
        await self.session.commit()
        return {
            "message": f"Revoked {count} session(s).",
            "sessions_revoked": count
        }

