"""Relationship and constraint tests for the domain schema."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import (
    ArticleStatus,
    Customer,
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    Organization,
    SLA,
    Team,
    TeamMember,
    Ticket,
    TicketAssignment,
    TicketComment,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)


async def _make_org(session: AsyncSession, slug: str = "acme") -> Organization:
    org = Organization(name="Acme", slug=slug)
    session.add(org)
    await session.flush()
    return org


async def _make_user(
    session: AsyncSession, org: Organization, email: str, role: UserRole = UserRole.AGENT
) -> User:
    user = User(
        organization_id=org.id,
        email=email,
        full_name="Test User",
        hashed_password=hash_password("pw"),
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_customer(session: AsyncSession, org: Organization, email: str) -> Customer:
    customer = Customer(
        organization_id=org.id, email=email, full_name="Test Customer"
    )
    session.add(customer)
    await session.flush()
    return customer


@pytest.mark.asyncio
async def test_user_belongs_to_organization(db: AsyncSession) -> None:
    org = await _make_org(db)
    user = await _make_user(db, org, "agent@example.test", UserRole.AGENT)

    loaded = await db.scalar(select(User).where(User.id == user.id))
    assert loaded is not None
    assert loaded.organization_id == org.id
    assert loaded.role == UserRole.AGENT


@pytest.mark.asyncio
async def test_user_email_unique_per_org(db: AsyncSession) -> None:
    org_a = await _make_org(db, slug="a")
    org_b = await _make_org(db, slug="b")

    await _make_user(db, org_a, "shared@example.test")

    # Same email in a different org is allowed.
    await _make_user(db, org_b, "shared@example.test")

    # Same email in same org is rejected.
    with pytest.raises(IntegrityError):
        await _make_user(db, org_a, "shared@example.test")


@pytest.mark.asyncio
async def test_ticket_relationships(db: AsyncSession) -> None:
    org = await _make_org(db)
    customer = await _make_customer(db, org, "c@example.test")
    agent = await _make_user(db, org, "agent@example.test")
    team = Team(organization_id=org.id, name="Tier 1")
    db.add(team)
    await db.flush()

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        assigned_agent_id=agent.id,
        team_id=team.id,
        title="Login broken",
        description="Cannot log in.",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
    )
    db.add(ticket)
    await db.flush()

    loaded = await db.scalar(select(Ticket).where(Ticket.id == ticket.id))
    assert loaded is not None
    assert loaded.customer.id == customer.id
    assert loaded.assigned_agent is not None
    assert loaded.assigned_agent.id == agent.id
    assert loaded.team is not None
    assert loaded.team.id == team.id


@pytest.mark.asyncio
async def test_ticket_comments_cascade_on_ticket_delete(db: AsyncSession) -> None:
    org = await _make_org(db)
    customer = await _make_customer(db, org, "c@example.test")

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        title="Needs help",
        description="...",
    )
    db.add(ticket)
    await db.flush()

    comment = TicketComment(
        organization_id=org.id,
        ticket_id=ticket.id,
        body="Working on it.",
    )
    db.add(comment)
    await db.flush()
    comment_id = comment.id

    await db.delete(ticket)
    await db.flush()

    remaining = await db.scalar(
        select(TicketComment).where(TicketComment.id == comment_id)
    )
    assert remaining is None


@pytest.mark.asyncio
async def test_ticket_assignment_history_is_preserved(db: AsyncSession) -> None:
    org = await _make_org(db)
    customer = await _make_customer(db, org, "c@example.test")
    agent = await _make_user(db, org, "agent@example.test")

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        title="Needs assignment",
        description="...",
    )
    db.add(ticket)
    await db.flush()

    db.add(
        TicketAssignment(
            organization_id=org.id,
            ticket_id=ticket.id,
            assigned_to_user_id=agent.id,
            assigned_by_user_id=agent.id,
            note="Initial assignment",
        )
    )
    await db.flush()

    loaded = await db.scalar(select(Ticket).where(Ticket.id == ticket.id))
    assert loaded is not None
    assert len(loaded.assignments) == 1
    assert loaded.assignments[0].assigned_to_user_id == agent.id


@pytest.mark.asyncio
async def test_deleting_assignee_nullifies_ticket_reference(db: AsyncSession) -> None:
    org = await _make_org(db)
    customer = await _make_customer(db, org, "c@example.test")
    agent = await _make_user(db, org, "agent@example.test")

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        assigned_agent_id=agent.id,
        title="Assigned ticket",
        description="...",
    )
    db.add(ticket)
    await db.flush()
    ticket_id = ticket.id

    await db.delete(agent)
    await db.flush()
    db.expire_all()

    reloaded = await db.scalar(select(Ticket).where(Ticket.id == ticket_id))
    assert reloaded is not None
    assert reloaded.assigned_agent_id is None


@pytest.mark.asyncio
async def test_team_member_unique(db: AsyncSession) -> None:
    org = await _make_org(db)
    user = await _make_user(db, org, "agent@example.test")
    team = Team(organization_id=org.id, name="Tier 1")
    db.add(team)
    await db.flush()

    db.add(TeamMember(organization_id=org.id, team_id=team.id, user_id=user.id))
    await db.flush()

    with pytest.raises(IntegrityError):
        db.add(TeamMember(organization_id=org.id, team_id=team.id, user_id=user.id))
        await db.flush()


@pytest.mark.asyncio
async def test_sla_unique_name_per_org(db: AsyncSession) -> None:
    org = await _make_org(db)
    db.add(
        SLA(
            organization_id=org.id,
            name="Standard",
            priority=TicketPriority.MEDIUM,
            first_response_minutes=60,
            resolution_minutes=480,
        )
    )
    await db.flush()

    with pytest.raises(IntegrityError):
        db.add(
            SLA(
                organization_id=org.id,
                name="Standard",
                priority=TicketPriority.HIGH,
                first_response_minutes=30,
                resolution_minutes=240,
            )
        )
        await db.flush()


@pytest.mark.asyncio
async def test_kb_article_slug_unique_per_org(db: AsyncSession) -> None:
    org = await _make_org(db)
    category = KnowledgeBaseCategory(organization_id=org.id, name="Guides")
    db.add(category)
    await db.flush()

    db.add(
        KnowledgeBaseArticle(
            organization_id=org.id,
            category_id=category.id,
            title="A",
            slug="shared-slug",
            body="...",
            status=ArticleStatus.PUBLISHED,
        )
    )
    await db.flush()

    with pytest.raises(IntegrityError):
        db.add(
            KnowledgeBaseArticle(
                organization_id=org.id,
                category_id=category.id,
                title="B",
                slug="shared-slug",
                body="...",
                status=ArticleStatus.DRAFT,
            )
        )
        await db.flush()


@pytest.mark.asyncio
async def test_organization_delete_cascades(db: AsyncSession) -> None:
    org = await _make_org(db)
    customer = await _make_customer(db, org, "c@example.test")

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        title="Cascade me",
        description="...",
    )
    db.add(ticket)
    await db.flush()
    ticket_id = ticket.id

    await db.delete(org)
    await db.flush()
    db.expire_all()

    assert await db.scalar(select(Ticket).where(Ticket.id == ticket_id)) is None
    assert await db.scalar(select(Customer).where(Customer.id == customer.id)) is None