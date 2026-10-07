"""Tenant-agnostic user data access.

User lookups by email are intentionally global because email is globally
unique. All other queries must scope by organization_id at the service or
endpoint layer.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.db.scalar(select(User).where(User.email == email))

    async def email_exists(self, email: str) -> bool:
        found = await self.db.scalar(select(User.id).where(User.email == email))
        return found is not None