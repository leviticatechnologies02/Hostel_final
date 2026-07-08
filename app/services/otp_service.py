"""OTP generation, verification, and management service"""
import random
import string
from datetime import UTC, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import OTPVerification
from app.repositories.user_repository import UserRepository
from app.config import get_settings

settings = get_settings()


class OTPService:
    """Service for managing OTP operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random numeric OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    async def create_otp(
        self,
        user_id: str,
        otp_type: str,
    ) -> str:
        """Create and store OTP for a user"""
        otp_code = self.generate_otp()
        
        # Hash the OTP (in production, use bcrypt)
        from app.core.security import hash_password
        otp_hash = hash_password(otp_code)
        
        # Create OTP record
        otp = OTPVerification(
            user_id=user_id,
            otp_code_hash=otp_hash,
            otp_type=otp_type,
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.otp_expiry_minutes),
            is_used=False,
            attempt_count=0,
        )
        self.session.add(otp)
        await self.session.flush()
        
        return otp_code
    
    async def verify_otp(
        self,
        user_id: str,
        otp_code: str,
        otp_type: str,
    ) -> bool:
        """Verify OTP for a user"""
        # Validate user_id is a UUID before querying
        import uuid as _uuid
        try:
            _uuid.UUID(user_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="user_id must be a valid UUID (use the user_id returned from registration, not your email).",
            )

        # Get the latest OTP for this user and type
        from sqlalchemy import select, desc
        stmt = (
            select(OTPVerification)
            .where(
                OTPVerification.user_id == user_id,
                OTPVerification.otp_type == otp_type,
                OTPVerification.is_used == False,
            )
            .order_by(desc(OTPVerification.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        otp = result.scalar_one_or_none()
        
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid OTP found for this user.",
            )
        
        # Check if OTP has expired
        if otp.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired.",
            )
        
        # Check attempt count
        if otp.attempt_count >= settings.otp_max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum OTP attempts exceeded.",
            )
        
        # Verify OTP
        from app.core.security import verify_password
        if not verify_password(otp_code, otp.otp_code_hash):
            otp.attempt_count += 1
            await self.session.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP.",
            )
        
        # Mark OTP as used
        otp.is_used = True
        await self.session.flush()
        
        return True
    
    async def send_otp_email(
        self,
        email: str,
        otp_code: str,
        otp_type: str,
    ) -> bool:
        """Send OTP via email. Falls back to console log in dev if SMTP not configured."""
        # Always log for easy debugging
        print(f"[OTP EMAIL] {email} → {otp_code} (type={otp_type})")

        from app.integrations.email import EmailService, _is_configured
        if not _is_configured():
            print("[OTP] Email not configured — OTP printed above (dev mode)")
            return True

        try:
            svc = EmailService()
            if otp_type == "password_reset":
                await svc.send_password_reset_otp(
                    recipient_email=email,
                    recipient_name=email.split("@")[0],
                    otp=otp_code,
                )
            else:
                await svc.send_registration_otp(
                    recipient_email=email,
                    recipient_name=email.split("@")[0],
                    otp=otp_code,
                )
            print(f"[OTP] Email sent to {email}")
        except Exception as exc:
            # Never block registration/reset due to email failure
            print(f"[OTP] Email send failed ({exc}) — OTP still valid: {otp_code}")

        return True

    async def send_otp_sms(
        self,
        phone: str,
        otp_code: str,
        otp_type: str,
    ) -> bool:
        """Send OTP via SMS using 2Factor.in. Falls back to console log if not configured."""
        print(f"[OTP SMS] {phone} → {otp_code} (type={otp_type})")
        try:
            from app.integrations.sms import TwoFactorSMSClient
            sms = TwoFactorSMSClient()
            result = await sms.send_otp(phone=phone, otp=otp_code)
            if result:
                print(f"[OTP] SMS sent to {phone}")
            else:
                print(f"[OTP] SMS send failed for {phone} — OTP still valid via email")
            return result
        except Exception as exc:
            # Never block registration/reset due to SMS failure
            print(f"[OTP] SMS send error ({exc}) — OTP still valid via email")
            return False

    async def send_otp(
        self,
        email: str,
        phone: str,
        otp_code: str,
        otp_type: str,
    ) -> None:
        """
        Send OTP via BOTH email and SMS simultaneously.
        Neither channel failing will block the OTP flow.
        """
        import asyncio
        await asyncio.gather(
            self.send_otp_email(email, otp_code, otp_type),
            self.send_otp_sms(phone, otp_code, otp_type),
            return_exceptions=True,
        )

    async def resend_otp(
        self,
        user_id: str,
        otp_type: str,
    ) -> str:
        """Resend OTP by invalidating old one and creating new one"""
        # Mark all previous OTPs as used
        from sqlalchemy import update
        stmt = (
            update(OTPVerification)
            .where(
                OTPVerification.user_id == user_id,
                OTPVerification.otp_type == otp_type,
                OTPVerification.is_used == False,
            )
            .values(is_used=True)
        )
        await self.session.execute(stmt)

        # Create new OTP
        otp_code = await self.create_otp(user_id, otp_type)
        return otp_code

