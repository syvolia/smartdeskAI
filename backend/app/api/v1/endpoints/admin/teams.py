"""Team administration. Reads available to staff, writes to admins."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.admin._guards import require_admin, require_staff
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models import Team, TeamMember, User, UserRole
from app.schemas.admin import (
    TeamCreateRequest,
    TeamListResponse,
    TeamMemberAddRequest,
    TeamMemberSummary,
    TeamResponse,
    TeamUpdateRequest,
)

router = APIRouter(prefix="/teams", tags=["admin"])


async def _to_response(db: AsyncSession, team: Team) -> TeamResponse:
    rows = list(
        (
            await db.scalars(
                select(TeamMember)
                .where(TeamMember.team_id == team.id)
                .options(selectinload(TeamMember.user))
            )
        ).all()
    )
    members = [
        TeamMemberSummary(
            user_id=m.user_id,
            full_name=m.user.full_name if m.user else "(removed)",
            email=m.user.email if m.user else "",
            role=m.user.role if m.user else UserRole.AGENT,
            role_in_team=m.role_in_team,
        )
        for m in rows
    ]
    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        members=members,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


@router.get(
    "",
    response_model=TeamListResponse,
    summary="List teams. Available to staff (admin or agent).",
)
async def list_teams(
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> TeamListResponse:
    teams = list(
        (
            await db.scalars(
                select(Team)
                .where(Team.organization_id == user.organization_id)
                .order_by(Team.name.asc())
            )
        ).all()
    )
    return TeamListResponse(
        items=[await _to_response(db, t) for t in teams],
        total=len(teams),
    )


@router.post(
    "",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a team (admin only).",
)
async def create_team(
    payload: TeamCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    existing = await db.scalar(
        select(Team).where(
            Team.organization_id == user.organization_id,
            Team.name == payload.name,
        )
    )
    if existing is not None:
        raise ConflictError("A team with this name already exists.")

    team = Team(
        organization_id=user.organization_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return await _to_response(db, team)


@router.patch(
    "/{team_id}",
    response_model=TeamResponse,
    summary="Update a team (admin only).",
)
async def update_team(
    team_id: uuid.UUID,
    payload: TeamUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == user.organization_id
        )
    )
    if team is None:
        raise NotFoundError("Team not found.")

    if payload.name is not None:
        team.name = payload.name
    if payload.description is not None:
        team.description = payload.description

    await db.commit()
    await db.refresh(team)
    return await _to_response(db, team)


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a team (admin only).",
)
async def delete_team(
    team_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == user.organization_id
        )
    )
    if team is None:
        raise NotFoundError("Team not found.")
    await db.delete(team)
    await db.commit()


@router.post(
    "/{team_id}/members",
    response_model=TeamResponse,
    summary="Add a member to a team (admin only).",
)
async def add_team_member(
    team_id: uuid.UUID,
    payload: TeamMemberAddRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == user.organization_id
        )
    )
    if team is None:
        raise NotFoundError("Team not found.")

    target = await db.scalar(
        select(User).where(
            User.id == payload.user_id,
            User.organization_id == user.organization_id,
        )
    )
    if target is None:
        raise NotFoundError("User not found.")
    if target.role == UserRole.CUSTOMER:
        raise ValidationError("Customers cannot be team members.")

    existing = await db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team.id, TeamMember.user_id == target.id
        )
    )
    if existing is not None:
        raise ConflictError("User is already a member of this team.")

    db.add(
        TeamMember(
            organization_id=user.organization_id,
            team_id=team.id,
            user_id=target.id,
            role_in_team=payload.role_in_team,
        )
    )
    await db.commit()
    return await _to_response(db, team)


@router.delete(
    "/{team_id}/members/{member_user_id}",
    response_model=TeamResponse,
    summary="Remove a member from a team (admin only).",
)
async def remove_team_member(
    team_id: uuid.UUID,
    member_user_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == user.organization_id
        )
    )
    if team is None:
        raise NotFoundError("Team not found.")

    member = await db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team.id, TeamMember.user_id == member_user_id
        )
    )
    if member is None:
        raise NotFoundError("Membership not found.")
    await db.delete(member)
    await db.commit()
    return await _to_response(db, team)