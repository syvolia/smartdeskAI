"""Recipient resolution for ticket events.

Each function returns the list of user ids who should receive the
notification, minus the actor, and minus anyone inactive.
"""

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TeamMember, User, UserRole


class RecipientResolver:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _active_user_ids(self, ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
        ids = list({i for i in ids if i is not None})
        if not ids:
            return set()
        rows = await self.db.scalars(
            select(User.id).where(User.id.in_(ids), User.is_active.is_(True))
        )
        return set(rows.all())

    async def for_assignee(
        self,
        *,
        assignee_id: uuid.UUID | None,
        actor_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        if assignee_id is None or assignee_id == actor_id:
            return []
        return sorted(await self._active_user_ids([assignee_id]))

    async def for_reassignment(
        self,
        *,
        previous_assignee_id: uuid.UUID | None,
        new_assignee_id: uuid.UUID | None,
        actor_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        candidates = {
            previous_assignee_id,
            new_assignee_id,
        } - {None, actor_id}
        return sorted(await self._active_user_ids(candidates))

    async def for_comment(
        self,
        *,
        ticket_assignee_id: uuid.UUID | None,
        team_id: uuid.UUID | None,
        commenter_id: uuid.UUID,
        is_internal: bool,
    ) -> list[uuid.UUID]:
        """Internal notes go to the assignee and the ticket team.
        Public replies go to the assignee only.
        """
        candidates: set[uuid.UUID] = set()
        if ticket_assignee_id is not None:
            candidates.add(ticket_assignee_id)

        if is_internal and team_id is not None:
            team_members = await self.db.scalars(
                select(TeamMember.user_id).where(TeamMember.team_id == team_id)
            )
            candidates.update(team_members.all())

        candidates.discard(commenter_id)
        return sorted(await self._active_user_ids(candidates))

    async def for_status_change(
        self,
        *,
        ticket_assignee_id: uuid.UUID | None,
        actor_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        return await self.for_assignee(
            assignee_id=ticket_assignee_id, actor_id=actor_id
        )

    async def for_sla(
        self,
        *,
        ticket_assignee_id: uuid.UUID | None,
        org_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """SLA alerts go to the assignee and all admins in the org."""
        candidates: set[uuid.UUID] = set()
        if ticket_assignee_id is not None:
            candidates.add(ticket_assignee_id)

        admins = await self.db.scalars(
            select(User.id).where(
                User.organization_id == org_id, User.role == UserRole.ADMIN
            )
        )
        candidates.update(admins.all())

        return sorted(await self._active_user_ids(candidates))