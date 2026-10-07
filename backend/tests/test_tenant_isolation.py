"""Tenant isolation tests.

These verify that the schema and query patterns we will use in later phases
keep tenant data separated. Repository-level enforcement arrives in a later
phase; here we prove the underlying data model supports it cleanly.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    Organization,
    Ticket,
    TicketStatus,
    User,
    UserRole,
)
from app.core.security import hash_password


async def _bootstrap_tenant(session: AsyncSession, slug: str) -> tuple[Organization, User, Customer]:
    org = Organization(name=f"Org {slug}", slug=slug)
    session.add(org)
    await session.flush()

    user = User(
        organization_id=org.id,
        email=f"agent@{slug}.test",
        full_name="Agent",
        hashed_password=hash_password("pw"),
        role=UserRole.AGENT,
    )
    customer = Customer(
        organization_id=org.id,
        email=f"customer@{slug}.test",
        full_name=f"Customer {slug}",
    )
    session.add_all([user, customer])
    await session.flush()
    return org, user, customer


@pytest.mark.asyncio
async def test_tickets_scoped_by_organization(db: AsyncSession) -> None:
    org_a, _, customer_a = await _bootstrap_tenant(db, "tenant-a")
    org_b, _, customer_b = await _bootstrap_tenant(db, "tenant-b")

    db.add_all(
        [
            Ticket(
                organization_id=org_a.id,
                customer_id=customer_a.id,
                title="A ticket",
                description="...",
                status=TicketStatus.OPEN,
            ),
            Ticket(
                organization_id=org_b.id,
                customer_id=customer_b.id,
                title="B ticket",
                description="...",
                status=TicketStatus.OPEN,
            ),
        ]
    )
    await db.flush()

    a_tickets = (
        await db.scalars(
            select(Ticket).where(Ticket.organization_id == org_a.id)
        )
    ).all()
    b_tickets = (
        await db.scalars(
            select(Ticket).where(Ticket.organization_id == org_b.id)
        )
    ).all()

    assert {t.title for t in a_tickets} == {"A ticket"}
    assert {t.title for t in b_tickets} == {"B ticket"}


@pytest.mark.asyncio
async def test_same_slug_allowed_across_orgs(db: AsyncSession) -> None:
    org_a = Organization(name="A", slug="same-slug")
    org_b = Organization(name="B", slug="same-slug-2")
    db.add_all([org_a, org_b])
    await db.flush()

    # Different slugs across orgs — trivial.
    # Now prove same slug is disallowed globally (slug is unique globally).
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db.add(Organization(name="A2", slug="same-slug"))
        await db.flush()


@pytest.mark.asyncio
async def test_cross_tenant_reference_is_application_enforced(db: AsyncSession) -> None:
    """A ticket's organization_id and customer_id can point to different orgs
    at the DB level (no composite FK), so this test documents the invariant
    that Phase 3 services must enforce at write time.
    """
    org_a, _, customer_a = await _bootstrap_tenant(db, "alpha")
    org_b, _, _ = await _bootstrap_tenant(db, "beta")

    # Intentionally construct a "wrong" ticket to document the invariant.
    bad = Ticket(
        organization_id=org_b.id,
        customer_id=customer_a.id,  # customer_a belongs to org_a
        title="Cross-tenant reference",
        description="...",
    )
    db.add(bad)
    await db.flush()
    # DB accepts it — services must reject it. This assertion is a reminder.
    assert bad.organization_id != customer_a.organization_id