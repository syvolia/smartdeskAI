"""Authentication endpoints: register, login, refresh, logout, me."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthResult, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
        user=UserResponse.model_validate(result.user),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth:register", 5, 3600))],
    summary="Create a new organization and its first admin user.",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    result = await service.register(payload)
    await db.commit()
    return _to_response(result)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit("auth:login", 10, 60))],
    summary="Exchange email and password for an access/refresh token pair.",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    result = await service.login(payload.email, payload.password)
    await db.commit()
    return _to_response(result)


@router.post(
    "/refresh",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit("auth:refresh", 30, 60))],
    summary="Rotate a refresh token for a new access/refresh pair.",
)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    result = await service.refresh(payload.refresh_token)
    await db.commit()
    return _to_response(result)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token.",
)
async def logout(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = AuthService(db)
    await service.logout(payload.refresh_token)
    await db.commit()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the currently authenticated user.",
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)