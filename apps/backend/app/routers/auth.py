"""Authentication endpoints."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.medical_db_models import User
from app.models.medical_schemas import (
    AuthResponse,
    TokenPairResponse,
    TokenRefreshRequest,
    UserBootstrapRequest,
    UserLoginRequest,
    UserProfile,
)
from app.security.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_user_from_refresh_token,
    hash_password,
    revoke_refresh_token,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/bootstrap", response_model=AuthResponse)
async def bootstrap_admin(payload: UserBootstrapRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    existing = await db.scalar(select(User.id).limit(1))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bootstrap already completed")

    user = User(
        email=payload.email.lower().strip(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    access_token, access_exp = create_access_token(user)
    refresh_token, _ = await create_refresh_token(user, db)

    return AuthResponse(
        user=UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_admin=user.is_admin,
            created_at=user.created_at,
        ),
        tokens=TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in_seconds=max(int((access_exp - datetime.datetime.now(datetime.UTC)).total_seconds()), 0),
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await authenticate_user(payload.email, payload.password, db)
    user.last_login_at = datetime.datetime.now(datetime.UTC)

    access_token, access_exp = create_access_token(user)
    refresh_token, _ = await create_refresh_token(user, db)

    return AuthResponse(
        user=UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_admin=user.is_admin,
            created_at=user.created_at,
        ),
        tokens=TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in_seconds=max(int((access_exp - datetime.datetime.now(datetime.UTC)).total_seconds()), 0),
        ),
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_tokens(payload: TokenRefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
    user = await get_user_from_refresh_token(payload.refresh_token, db)
    await revoke_refresh_token(payload.refresh_token, db)

    access_token, access_exp = create_access_token(user)
    refresh_token, _ = await create_refresh_token(user, db)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_seconds=max(int((access_exp - datetime.datetime.now(datetime.UTC)).total_seconds()), 0),
    )
