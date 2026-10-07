"""Ticket business logic: CRUD, assignment, status, priority, comments, events."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models import (
    Customer,
    Team,
    Ticket,
    TicketCategory,
    TicketComment,
    TicketEventType,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.notifications.service import NotificationService
from app.repositories.ticket_event_repository import TicketEventRepository
from app.repositories.ticket_repository import TicketFilters, TicketRepository
from app.schemas.ticket import (
    TicketAssignRequest,
    TicketCommentCreateRequest,
    TicketCreateRequest,
    TicketPriorityChangeRequest,
    TicketStatusChangeRequest,
    TicketUpdateRequest,
)
from app.services.sla_service import SLAService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TicketService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        notifications: NotificationService | None = None,
    ) -> None:
        self.db = db
        self.repo = TicketRepository(db)
        self.events = TicketEventRepository(db)
        self.sla = SLAService(db)
        self.notifications = notifications

    # ---------- access helpers ----------

    @staticmethod
    def _is_staff(user: User) -> bool:
        return user.role in (UserRole.ADMIN, UserRole.AGENT)

    @staticmethod
    def _is_admin(user: User) -> bool:
        return user.role == UserRole.ADMIN

    async def _load_customer(self, customer_id, org_id):
        customer = await self.db.scalar(
            select(Customer).where(
                Customer.id == customer_id, Customer.organization_id == org_id
            )
        )
        if customer is None:
            raise NotFoundError("Customer not found.")
        return customer

    async def _load_agent(self, agent_id, org_id):
        user = await self.db.scalar(
            select(User).where(
                User.id == agent_id,
                User.organization_id == org_id,
                User.is_active.is_(True),
            )
        )
        if user is None or user.role == UserRole.CUSTOMER:
            raise ValidationError("Assignee must be an agent in this organization.")
        return user

    async def _load_team(self, team_id, org_id):
        team = await self.db.scalar(
            select(Team).where(Team.id == team_id, Team.organization_id == org_id)
        )
        if team is None:
            raise NotFoundError("Team not found.")
        return team

    async def _load_category(self, category_id, org_id):
        category = await self.db.scalar(
            select(TicketCategory).where(
                TicketCategory.id == category_id,
                TicketCategory.organization_id == org_id,
            )
        )
        if category is None:
            raise NotFoundError("Category not found.")
        return category

    async def _reload(self, ticket: Ticket) -> Ticket:
        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket.id)
            .options(
                selectinload(Ticket.customer),
                selectinload(Ticket.assigned_agent),
                selectinload(Ticket.team),
                selectinload(Ticket.category),
                selectinload(Ticket.sla_policy),
            )
            .execution_options(populate_existing=True)
        )
        fresh = await self.db.scalar(stmt)
        assert fresh is not None
        return fresh

    def _enforce_read_access(self, ticket: Ticket, user: User) -> None:
        if self._is_staff(user):
            return
        if ticket.customer.email != user.email:
            raise NotFoundError("Ticket not found.")

    def _enforce_write_access(self, ticket: Ticket, user: User) -> None:
        if self._is_staff(user):
            return
        raise ForbiddenError("You do not have permission to modify this ticket.")

    # ---------- create ----------

    async def create(self, user: User, data: TicketCreateRequest) -> Ticket:
        org_id = user.organization_id

        if self._is_staff(user):
            customer = await self._load_customer(data.customer_id, org_id)
        else:
            customer = await self.db.scalar(
                select(Customer).where(
                    Customer.organization_id == org_id,
                    Customer.email == user.email,
                )
            )
            if customer is None or customer.id != data.customer_id:
                raise ForbiddenError(
                    "Customers can only open tickets for their own account."
                )

        team = None
        if data.team_id is not None:
            team = await self._load_team(data.team_id, org_id)
        agent = None
        if data.assigned_agent_id is not None:
            agent = await self._load_agent(data.assigned_agent_id, org_id)
        category = None
        if data.category_id is not None:
            category = await self._load_category(data.category_id, org_id)

        ticket = Ticket(
            organization_id=org_id,
            customer_id=customer.id,
            assigned_agent_id=agent.id if agent else None,
            team_id=team.id if team else None,
            category_id=category.id if category else None,
            title=data.title,
            description=data.description,
            status=TicketStatus.OPEN,
            priority=data.priority,
            source=data.source,
        )
        await self.repo.add(ticket)
        await self.db.refresh(ticket)

        policy = await self.sla.apply_policy(ticket)
        if policy is not None:
            await self.events.add(
                organization_id=org_id,
                ticket_id=ticket.id,
                actor_user_id=user.id,
                event_type=TicketEventType.SLA_POLICY_APPLIED,
                to_value=policy.name,
                details={"priority": ticket.priority.value},
            )

        await self.events.add(
            organization_id=org_id,
            ticket_id=ticket.id,
            actor_user_id=user.id,
            event_type=TicketEventType.TICKET_CREATED,
            to_value=ticket.status.value,
        )

        if agent is not None:
            await self.events.add(
                organization_id=org_id,
                ticket_id=ticket.id,
                actor_user_id=user.id,
                event_type=TicketEventType.TICKET_ASSIGNED,
                to_value=str(agent.id),
                details={"assignee_email": agent.email},
            )
            if self.notifications is not None:
                reloaded = await self._reload(ticket)
                await self.notifications.on_ticket_assigned(reloaded, user)

        await self.db.flush()
        return await self._reload(ticket)

    # ---------- read ----------

    async def get(self, ticket_id, user):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_read_access(ticket, user)
        return ticket

    async def list_tickets(
        self,
        user,
        *,
        filters: TicketFilters,
        sort: str,
        order: str,
        page: int,
        page_size: int,
    ):
        if not self._is_staff(user):
            filters.restrict_customer_email = user.email
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        return await self.repo.list_paginated(
            user.organization_id,
            filters=filters,
            sort=sort,
            order=order,
            page=page,
            page_size=page_size,
        )

    # ---------- update ----------

    async def update(self, ticket_id, user, data: TicketUpdateRequest):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_write_access(ticket, user)

        changes: dict = {}
        payload = data.model_dump(exclude_unset=True)

        if "title" in payload and payload["title"] is not None:
            changes["title"] = (ticket.title, payload["title"])
            ticket.title = payload["title"]
        if "description" in payload and payload["description"] is not None:
            changes["description"] = "updated"
            ticket.description = payload["description"]
        if "category_id" in payload:
            new_id = payload["category_id"]
            if new_id is None:
                changes["category"] = (ticket.category_id, None)
                ticket.category_id = None
            else:
                category = await self._load_category(new_id, user.organization_id)
                changes["category"] = (ticket.category_id, category.id)
                ticket.category_id = category.id

        if changes:
            await self.events.add(
                organization_id=user.organization_id,
                ticket_id=ticket.id,
                actor_user_id=user.id,
                event_type=TicketEventType.TICKET_UPDATED,
                details=changes,
            )
            await self.db.flush()

        return await self._reload(ticket)

    async def delete(self, ticket_id, user):
        if not self._is_admin(user):
            raise ForbiddenError("Only administrators can delete tickets.")
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        await self.repo.delete(ticket)

    # ---------- assign ----------

    async def assign(self, ticket_id, user, data: TicketAssignRequest):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_write_access(ticket, user)

        old_agent_id = ticket.assigned_agent_id
        old_team_id = ticket.team_id
        new_agent_id = data.assigned_agent_id
        new_team_id = data.team_id

        if new_agent_id is not None:
            await self._load_agent(new_agent_id, user.organization_id)
        if new_team_id is not None:
            await self._load_team(new_team_id, user.organization_id)

        if new_agent_id == old_agent_id and new_team_id == old_team_id:
            return await self._reload(ticket)

        ticket.assigned_agent_id = new_agent_id
        ticket.team_id = new_team_id

        was_assigned = old_agent_id is not None or old_team_id is not None
        event_type = (
            TicketEventType.TICKET_REASSIGNED
            if was_assigned
            else TicketEventType.TICKET_ASSIGNED
        )

        await self.events.add(
            organization_id=user.organization_id,
            ticket_id=ticket.id,
            actor_user_id=user.id,
            event_type=event_type,
            from_value=str(old_agent_id) if old_agent_id else None,
            to_value=str(new_agent_id) if new_agent_id else None,
            note=data.note,
            details={
                "from_team_id": str(old_team_id) if old_team_id else None,
                "to_team_id": str(new_team_id) if new_team_id else None,
            },
        )
        await self.db.flush()

        reloaded = await self._reload(ticket)
        if self.notifications is not None:
            if was_assigned:
                await self.notifications.on_ticket_reassigned(
                    reloaded, user, previous_assignee_id=old_agent_id
                )
            else:
                await self.notifications.on_ticket_assigned(reloaded, user)

        return reloaded

    # ---------- status ----------

    async def change_status(
        self, ticket_id, user, data: TicketStatusChangeRequest
    ):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_write_access(ticket, user)

        old = ticket.status
        new = data.status
        if old == new:
            return await self._reload(ticket)

        now = _utcnow()
        ticket.status = new

        if new == TicketStatus.RESOLVED and ticket.resolved_at is None:
            ticket.resolved_at = now
        if new == TicketStatus.CLOSED:
            ticket.closed_at = now
            if ticket.resolved_at is None:
                ticket.resolved_at = now

        reopened = old in (TicketStatus.RESOLVED, TicketStatus.CLOSED) and new not in (
            TicketStatus.RESOLVED,
            TicketStatus.CLOSED,
        )
        if reopened:
            ticket.resolved_at = None
            ticket.closed_at = None

        if (
            self._is_staff(user)
            and old == TicketStatus.OPEN
            and new != TicketStatus.OPEN
            and ticket.first_response_at is None
        ):
            ticket.first_response_at = now

        if new == TicketStatus.RESOLVED:
            event_type = TicketEventType.TICKET_RESOLVED
        elif new == TicketStatus.CLOSED:
            event_type = TicketEventType.TICKET_CLOSED
        elif reopened:
            event_type = TicketEventType.TICKET_REOPENED
        else:
            event_type = TicketEventType.STATUS_CHANGED

        await self.events.add(
            organization_id=user.organization_id,
            ticket_id=ticket.id,
            actor_user_id=user.id,
            event_type=event_type,
            from_value=old.value,
            to_value=new.value,
            note=data.note,
        )

        snapshot = self.sla.evaluate(ticket, now=now)
        if snapshot.sla_breached and not ticket.sla_breached:
            ticket.sla_breached = True
            await self.events.add(
                organization_id=user.organization_id,
                ticket_id=ticket.id,
                actor_user_id=user.id,
                event_type=TicketEventType.SLA_BREACHED,
                details={
                    "first_response_breached": snapshot.first_response_breached,
                    "resolution_breached": snapshot.resolution_breached,
                },
            )

        await self.db.flush()
        reloaded = await self._reload(ticket)

        if self.notifications is not None:
            if new == TicketStatus.RESOLVED:
                await self.notifications.on_ticket_resolved(reloaded, user)
            elif reopened:
                await self.notifications.on_ticket_reopened(reloaded, user)

        return reloaded

    # ---------- priority ----------

    async def change_priority(
        self, ticket_id, user, data: TicketPriorityChangeRequest
    ):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_write_access(ticket, user)

        old = ticket.priority
        new = data.priority
        if old == new:
            return await self._reload(ticket)

        ticket.priority = new
        policy = await self.sla.apply_policy(ticket)

        await self.events.add(
            organization_id=user.organization_id,
            ticket_id=ticket.id,
            actor_user_id=user.id,
            event_type=TicketEventType.PRIORITY_CHANGED,
            from_value=old.value,
            to_value=new.value,
            note=data.note,
            details={"sla_policy": policy.name if policy else None},
        )
        await self.db.flush()
        return await self._reload(ticket)

    # ---------- comments ----------

    async def add_comment(
        self, ticket_id, user, data: TicketCommentCreateRequest
    ):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_read_access(ticket, user)

        if data.is_internal and not self._is_staff(user):
            raise ForbiddenError("Only staff can post internal notes.")

        comment = TicketComment(
            organization_id=user.organization_id,
            ticket_id=ticket.id,
            author_user_id=user.id,
            body=data.body,
            is_internal=data.is_internal,
        )
        self.db.add(comment)
        await self.db.flush()

        if (
            self._is_staff(user)
            and not data.is_internal
            and ticket.first_response_at is None
        ):
            ticket.first_response_at = _utcnow()

        await self.events.add(
            organization_id=user.organization_id,
            ticket_id=ticket.id,
            actor_user_id=user.id,
            event_type=TicketEventType.COMMENT_ADDED,
            details={"is_internal": data.is_internal, "comment_id": str(comment.id)},
        )
        await self.db.flush()

        if self.notifications is not None:
            reloaded = await self._reload(ticket)
            await self.notifications.on_comment_added(reloaded, comment, user)

        return comment

    async def list_comments(self, ticket_id, user):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_read_access(ticket, user)

        stmt = (
            select(TicketComment)
            .where(
                TicketComment.ticket_id == ticket.id,
                TicketComment.organization_id == user.organization_id,
            )
            .options(selectinload(TicketComment.author))
            .order_by(TicketComment.created_at.asc(), TicketComment.id.asc())
        )
        if not self._is_staff(user):
            stmt = stmt.where(TicketComment.is_internal.is_(False))

        return list((await self.db.scalars(stmt)).all())

    async def list_events(self, ticket_id, user, *, limit=100, offset=0):
        ticket = await self.repo.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._enforce_read_access(ticket, user)
        return await self.events.list_for_ticket(
            ticket.id, user.organization_id, limit=limit, offset=offset
        )