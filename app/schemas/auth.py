from pydantic import BaseModel, EmailStr, Field, field_validator


class VisitorRegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=30)
    password: str = Field(min_length=8, max_length=128)


class VisitorRegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    phone: str
    message: str


class LoginRequest(BaseModel):
    email_or_phone: str
    password: str

    @field_validator("email_or_phone", "password", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email_or_phone": "superadmin@stayease.com",
                    "password": "Test@1234"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str = ""
    hostel_ids: list[str] = []
    expires_in: int = 900


class AccessTokenResponse(BaseModel):
    """
    Response model for auth endpoints that return only an access token.
    Refresh token must be stored/rotated via httpOnly cookie.
    """

    user_id: str
    access_token: str
    token_type: str = "bearer"
    role: str = ""
    hostel_ids: list[str] = []
    expires_in: int = 900


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class OTPVerifyRequest(BaseModel):
    user_id: str
    otp_code: str = Field(min_length=4, max_length=8)


class ResendOTPRequest(BaseModel):
    user_id: str


class ResetPasswordRequest(BaseModel):
    user_id: str
    otp_code: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    # Backend supports email or phone, but the UI uses email.
    email_or_phone: str

    @field_validator("email_or_phone", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
