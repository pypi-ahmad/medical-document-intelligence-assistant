"""Authentication and authorization helpers."""

from __future__ import annotations

import datetime
import hashlib
import secrets
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.medical_db_models import RefreshToken, User

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        super().__init__(status_code=status_code, detail=detail)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def _token_expiry(minutes: int) -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=minutes)


def _token_expiry_days(days: int) -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user: User) -> tuple[str, datetime.datetime]:
    expires_at = _token_expiry(settings.access_token_expire_minutes)
    payload = {
        "sub": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "type": "access",
        "exp": expires_at,
        "iat": datetime.datetime.now(datetime.UTC),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


async def create_refresh_token(user: User, db: AsyncSession) -> tuple[str, datetime.datetime]:
    expires_at = _token_expiry_days(settings.refresh_token_expire_days)
    raw_token = secrets.token_urlsafe(64)
    payload = {
        "sub": user.id,
        "type": "refresh",
        "jti": raw_token,
        "exp": expires_at,
        "iat": datetime.datetime.now(datetime.UTC),
    }
    signed_token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_token_digest(signed_token),
            expires_at=expires_at,
        )
    )
    await db.flush()
    return signed_token, expires_at


async def revoke_refresh_token(token: str, db: AsyncSession) -> None:
    token_hash = _token_digest(token)
    record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if record and record.revoked_at is None:
        record.revoked_at = datetime.datetime.now(datetime.UTC)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired token") from exc


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    user = await db.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None or not user.is_active:
        raise AuthError("Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid credentials")
    return user


async def _get_or_create_local_dev_user(db: AsyncSession) -> User:
    user = await db.scalar(select(User).where(User.email == "local-dev@localhost"))
    if user is not None:
        return user
    user = User(
        email="local-dev@localhost",
        full_name="Local Dev User",
        password_hash=hash_password("local-dev-auth-disabled"),
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def get_user_from_access_token(token: str, db: AsyncSession) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthError("Invalid token type")
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise AuthError("Invalid token subject")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("User not found")
    return user


async def get_user_from_refresh_token(token: str, db: AsyncSession) -> User:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type")
    token_hash = _token_digest(token)
    refresh = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if refresh is None or refresh.revoked_at is not None:
        raise AuthError("Refresh token revoked")
    if refresh.expires_at < datetime.datetime.now(datetime.UTC):
        raise AuthError("Refresh token expired")
    user = await db.get(User, refresh.user_id)
    if user is None or not user.is_active:
        raise AuthError("User not found")
    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not settings.enable_auth:
        return await _get_or_create_local_dev_user(db)
    if credentials is None:
        raise AuthError("Missing bearer token")
    return await get_user_from_access_token(credentials.credentials, db)


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_admin:
        raise AuthError("Admin role required", status_code=status.HTTP_403_FORBIDDEN)
    return user
