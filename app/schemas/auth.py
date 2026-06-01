import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    timezone: str = Field(default="UTC", max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    timezone: str
    created_at: datetime
    otp_enabled: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginResponse(BaseModel):
    """Returned by POST /auth/login.
    If requires_2fa is True, access_token is absent and temp_token must be
    passed to POST /auth/2fa/validate to obtain the real access token.
    """
    requires_2fa: bool = False
    temp_token: str | None = None
    access_token: str | None = None
    token_type: str = "bearer"
    user: UserOut | None = None


# ── 2FA schemas ───────────────────────────────────────────────────────────────

class TwoFactorEnableResponse(BaseModel):
    qr_code: str        # base64-encoded PNG
    secret: str         # plaintext backup (user should save this)
    message: str


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TwoFactorValidateRequest(BaseModel):
    temp_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
