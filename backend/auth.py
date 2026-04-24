"""
JWT-based authentication — register, login, refresh, forgot/reset password.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

import db
from config import (
    SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS, RESEND_API_KEY, FROM_EMAIL, FRONTEND_URL,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

ALGORITHM = "HS256"


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return pwd_context.hash(password)

def _verify(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def _access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def _refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh"},
        SECRET_KEY, algorithm=ALGORITHM
    )

def _token_response(user_id: int, email: str) -> dict:
    return {
        "access_token": _access_token(user_id),
        "refresh_token": _refresh_token(user_id),
        "token_type": "bearer",
        "user": {"id": user_id, "email": email},
    }


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(data: RegisterRequest):
    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if db.get_user_by_email(data.email):
        raise HTTPException(400, "Email already registered")
    user_id = db.create_user(data.email, _hash(data.password))
    return _token_response(user_id, data.email.lower().strip())


@router.post("/login")
async def login(data: LoginRequest):
    user = db.get_user_by_email(data.email)
    if not user or not _verify(data.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid email or password")
    return _token_response(user["id"], user["email"])


@router.post("/refresh")
async def refresh(data: RefreshRequest):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired refresh token")
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return {"access_token": _access_token(user_id), "token_type": "bearer"}


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    user = db.get_user_by_email(data.email)
    # Always 200 — prevents email enumeration
    if not user:
        return {"message": "If that email exists, a reset link has been sent"}

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    db.create_reset_token(user["id"], token, expires_at)
    reset_url = f"{FRONTEND_URL}?reset_token={token}"

    if RESEND_API_KEY:
        try:
            import resend
            resend.api_key = RESEND_API_KEY
            resend.Emails.send({
                "from": FROM_EMAIL,
                "to": data.email,
                "subject": "Reset your EdgeLayer password",
                "html": (
                    f"<p>Click the link below to reset your EdgeLayer password. "
                    f"The link expires in 1 hour.</p>"
                    f'<p><a href="{reset_url}">{reset_url}</a></p>'
                    f"<p>If you did not request a password reset, ignore this email.</p>"
                ),
            })
            logger.info(f"Password reset email sent to {data.email}")
        except Exception as e:
            logger.error(f"Failed to send reset email: {e}")
    else:
        logger.warning(f"RESEND_API_KEY not set — reset token: {token}")

    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    record = db.get_reset_token(data.token)
    if not record:
        raise HTTPException(400, "Invalid or expired reset token")
    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(400, "Reset token has expired")
    db.update_user_password(record["user_id"], _hash(data.password))
    db.mark_reset_token_used(data.token)
    return {"message": "Password updated successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"id": current_user["id"], "email": current_user["email"]}
