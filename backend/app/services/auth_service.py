"""Authentication service: register, login, refresh, logout."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import Organization, User, UserRole
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest
from app.core.config import settings


@dataclass
class AuthResult:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    # ---------- public API ----------

    async def register(self, data: RegisterRequest) -> AuthResult:
        if await self.users.email_exists(data.email):
            raise ConflictError("An account with this email already exists.")

        existing_org = await self.db.scalar(
            select(Organization).where(Organization.slug == data.organization_slug)
        )
        if existing_org is not None:
            raise ConflictError("An organization with this slug already exists.")

        org = Organization(name=data.organization_name, slug=data.organization_slug)
        self.db.add(org)
        await self.db.flush()

        user = User(
            organization_id=org.id,
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=UserRole.ADMIN,
        )
        self.db.add(user)
        await self.db.flush()

        return await self._issue_tokens(user)

    async def login(self, email: str, password: str) -> AuthResult:
        user = await self.users.get_by_email(email)

        # Constant-ish failure mode: same error for unknown email and bad pw.
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise ForbiddenError("Account is disabled.")

        return await self._issue_tokens(user)

    async def refresh(self, raw_refresh_token: str) -> AuthResult:
        token_hash = hash_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)

        if stored is None:
            raise UnauthorizedError("Invalid refresh token.")
        if stored.revoked_at is not None:
            raise UnauthorizedError("Refresh token has been revoked.")
        if stored.expires_at <= datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token has expired.")

        user = await self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User is no longer active.")

        # Rotate: revoke old, issue a fresh pair.
        await self.refresh_tokens.revoke(stored)
        return await self._issue_tokens(user)

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)
        if stored is not None and stored.revoked_at is None:
            await self.refresh_tokens.revoke(stored)

    # ---------- internals ----------

    async def _issue_tokens(self, user: User) -> AuthResult:
        access_token, _ = create_access_token(user.id)
        raw_refresh, refresh_hash, refresh_expires = create_refresh_token()

        await self.refresh_tokens.create(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_expires,
        )

        return AuthResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in= settings.access_token_expire_minutes * 60,  # matches settings.access_token_expire_minutes default
            user=user,
        )