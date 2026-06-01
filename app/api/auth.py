import base64
import io

import jwt
import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
    TwoFactorEnableResponse,
    TwoFactorValidateRequest,
    TwoFactorVerifyRequest,
    UserOut,
)
from app.security import (
    create_access_token,
    create_temp_token,
    decode_temp_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

APP_NAME = "Habit Tracker"


# ── Standard auth ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_session)):
    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        timezone=data.timezone,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    await session.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = (
        await session.execute(select(User).where(User.email == data.email.lower()))
    ).scalar_one_or_none()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if user.otp_enabled and user.otp_verified:
        # Password OK but 2FA required — return a short-lived temp token
        return LoginResponse(
            requires_2fa=True,
            temp_token=create_temp_token(user.id),
        )

    # No 2FA — issue full access token immediately
    return LoginResponse(
        requires_2fa=False,
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    return current


# ── Two-Factor Authentication ─────────────────────────────────────────────────

@router.post("/2fa/enable", response_model=TwoFactorEnableResponse)
async def enable_2fa(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate a new TOTP secret and return a QR code for the authenticator app."""
    secret = pyotp.random_base32()

    # Persist the secret (not yet verified/enabled — user must confirm with a code)
    current.otp_secret = secret
    current.otp_enabled = False
    current.otp_verified = False
    await session.commit()

    # Build the otpauth:// URI and render it as a QR code PNG
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current.email, issuer_name=APP_NAME)

    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return TwoFactorEnableResponse(
        qr_code=qr_b64,
        secret=secret,
        message=f"Scan the QR code with {APP_NAME} in your authenticator app, "
                "then confirm with POST /auth/2fa/verify-setup",
    )


@router.post("/2fa/verify-setup", status_code=status.HTTP_200_OK)
async def verify_2fa_setup(
    data: TwoFactorVerifyRequest,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Confirm the authenticator app is working; activates 2FA on the account."""
    if not current.otp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call /auth/2fa/enable first to generate a secret",
        )

    totp = pyotp.TOTP(current.otp_secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code — make sure your authenticator app clock is correct",
        )

    current.otp_enabled = True
    current.otp_verified = True
    await session.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/validate", response_model=TokenResponse)
async def validate_2fa(
    data: TwoFactorValidateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Exchange a temp token + TOTP code for a full access token."""
    try:
        user_id = decode_temp_token(data.temp_token)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary token",
        )

    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None or not user.otp_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    totp = pyotp.TOTP(user.otp_secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/2fa/disable", status_code=status.HTTP_200_OK)
async def disable_2fa(
    data: TwoFactorVerifyRequest,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Disable 2FA — requires a valid TOTP code to confirm identity."""
    if not current.otp_enabled or not current.otp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled on this account",
        )

    totp = pyotp.TOTP(current.otp_secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code — 2FA not disabled",
        )

    current.otp_secret = None
    current.otp_enabled = False
    current.otp_verified = False
    await session.commit()
    return {"message": "2FA disabled successfully"}
