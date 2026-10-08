"""Seed SmartDesk AI with demo data.

Idempotent: deletes any existing organization whose slug is `demo`, then
creates a fresh, deterministic dataset.

Run:
    cd backend && python -m app.scripts.seed

Demo accounts (password `Demo123!` for all):
    Admin    → admin@smartdesk-demo.dev
    Agent    → agent1@smartdesk-demo.dev
    Customer → customer@smartdesk-demo.dev
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import SessionLocal, dispose_engine
from app.models import (
    ArticleStatus,
    AuditLog,
    Customer,
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    Notification,
    NotificationType,
    Organization,
    SLA,
    Team,
    TeamMember,
    Ticket,
    TicketAssignment,
    TicketCategory,
    TicketComment,
    TicketPriority,
    TicketSource,
    TicketStatus,
    User,
    UserRole,
)

DEMO_ORG_SLUG = "demo"
DEMO_PASSWORD = "Demo123!"
DEMO_CUSTOMER_EMAIL = "customer@smartdesk-demo.dev"
RNG = random.Random(42)


TICKET_TEMPLATES: list[tuple[str, str, TicketStatus, TicketPriority, TicketSource]] = [
    ("Cannot log in to my account", "Password reset link expires too quickly. Please help.", TicketStatus.OPEN, TicketPriority.HIGH, TicketSource.EMAIL),
    ("Billing charged twice this month", "I see two identical charges on my card statement.", TicketStatus.IN_PROGRESS, TicketPriority.URGENT, TicketSource.WEB),
    ("Export to CSV is failing", "The export button returns an empty file for large datasets.", TicketStatus.IN_PROGRESS, TicketPriority.MEDIUM, TicketSource.WEB),
    ("Feature request: dark mode", "Please add a dark theme for the dashboard.", TicketStatus.OPEN, TicketPriority.LOW, TicketSource.CHAT),
    ("API returns 500 on /v1/orders", "Our integration started failing 30 minutes ago.", TicketStatus.IN_PROGRESS, TicketPriority.URGENT, TicketSource.API),
    ("Need invoice for last quarter", "Please email the Q3 invoice PDF.", TicketStatus.WAITING_CUSTOMER, TicketPriority.LOW, TicketSource.EMAIL),
    ("Mobile app crashes on startup", "iOS 17, iPhone 14. Happens every launch.", TicketStatus.OPEN, TicketPriority.HIGH, TicketSource.WEB),
    ("How do I add a teammate?", "I can't find the invite option in settings.", TicketStatus.RESOLVED, TicketPriority.LOW, TicketSource.CHAT),
    ("Data import stalls at 80%", "CSV upload of ~50k rows hangs indefinitely.", TicketStatus.IN_PROGRESS, TicketPriority.HIGH, TicketSource.WEB),
    ("2FA codes not arriving", "SMS codes never arrive on my phone number.", TicketStatus.WAITING_CUSTOMER, TicketPriority.HIGH, TicketSource.PHONE),
    ("Wrong currency shown on invoices", "Invoices show USD but our account is EUR.", TicketStatus.OPEN, TicketPriority.MEDIUM, TicketSource.EMAIL),
    ("Cannot delete a workspace", "Delete button is greyed out for admin user.", TicketStatus.OPEN, TicketPriority.MEDIUM, TicketSource.WEB),
    ("Webhook signature verification fails", "Following docs but HMAC mismatch every time.", TicketStatus.IN_PROGRESS, TicketPriority.HIGH, TicketSource.API),
    ("Request to increase rate limit", "We're hitting 429s during peak hours.", TicketStatus.WAITING_CUSTOMER, TicketPriority.MEDIUM, TicketSource.EMAIL),
    ("SSO login loop", "After Okta login, redirected back to login page.", TicketStatus.IN_PROGRESS, TicketPriority.URGENT, TicketSource.EMAIL),
    ("Attachment upload maximum size", "What is the max file size for uploads?", TicketStatus.RESOLVED, TicketPriority.LOW, TicketSource.CHAT),
    ("Search returns no results for accented text", "Queries with é, ü, ñ return zero hits.", TicketStatus.OPEN, TicketPriority.MEDIUM, TicketSource.WEB),
    ("Need SOC 2 report", "Procurement is asking for the latest SOC 2.", TicketStatus.WAITING_CUSTOMER, TicketPriority.LOW, TicketSource.EMAIL),
    ("Time zone mismatch on reports", "Reports show UTC, but our org is Europe/Berlin.", TicketStatus.CLOSED, TicketPriority.MEDIUM, TicketSource.WEB),
    ("User provisioned with wrong role", "New hire received admin instead of agent.", TicketStatus.RESOLVED, TicketPriority.HIGH, TicketSource.PHONE),
]


async def _delete_demo_org(session: AsyncSession) -> None:
    org_id = await session.scalar(
        select(Organization.id).where(Organization.slug == DEMO_ORG_SLUG)
    )
    if org_id is None:
        return
    await session.execute(delete(Organization).where(Organization.id == org_id))
    await session.flush()


async def seed(session: AsyncSession) -> None:
    await _delete_demo_org(session)

    # --- Organization ---
    org = Organization(name="Acme Demo Corp", slug=DEMO_ORG_SLUG)
    session.add(org)
    await session.flush()

    # --- Users: 1 admin + 3 agents ---
    password_hash = hash_password(DEMO_PASSWORD)
    admin = User(
        organization_id=org.id,
        email="admin@smartdesk-demo.dev",
        full_name="Ada Admin",
        hashed_password=password_hash,
        role=UserRole.ADMIN,
    )
    agents = [
        User(
            organization_id=org.id,
            email=f"agent{i}@smartdesk-demo.dev",
            full_name=name,
            hashed_password=password_hash,
            role=UserRole.AGENT,
        )
        for i, name in enumerate(
            ["Grace Agent", "Linus Agent", "Margaret Agent"], start=1
        )
    ]
    session.add_all([admin, *agents])
    await session.flush()

    # --- Teams ---
    team_tier1 = Team(
        organization_id=org.id,
        name="Tier 1 Support",
        description="Front-line support for common issues.",
    )
    team_tier2 = Team(
        organization_id=org.id,
        name="Tier 2 Escalations",
        description="Engineering escalations and complex issues.",
    )
    session.add_all([team_tier1, team_tier2])
    await session.flush()

    session.add_all(
        [
            TeamMember(organization_id=org.id, team_id=team_tier1.id, user_id=agents[0].id, role_in_team="lead"),
            TeamMember(organization_id=org.id, team_id=team_tier1.id, user_id=agents[1].id),
            TeamMember(organization_id=org.id, team_id=team_tier2.id, user_id=agents[2].id, role_in_team="lead"),
        ]
    )
    await session.flush()

    # --- Ticket categories ---
    categories = [
        TicketCategory(organization_id=org.id, name="Billing", description="Invoices, payments, plans."),
        TicketCategory(organization_id=org.id, name="Authentication", description="Login, SSO, 2FA."),
        TicketCategory(organization_id=org.id, name="Data & Integrations", description="Imports, exports, API, webhooks."),
        TicketCategory(organization_id=org.id, name="Mobile", description="iOS and Android app issues."),
        TicketCategory(organization_id=org.id, name="Feature Request", description="Product suggestions."),
    ]
    session.add_all(categories)
    await session.flush()

    # --- Customers ---
    # The first customer has a matching User account (below) so visitors
    # can log in with the CUSTOMER role and see the customer-side view.
    customers = [
        Customer(
            organization_id=org.id,
            email=DEMO_CUSTOMER_EMAIL,
            full_name="Casey Customer",
            company="Acme Demo Corp",
            phone="+1-555-0100",
        ),
        *[
            Customer(
                organization_id=org.id,
                email=f"customer{i}@example.test",
                full_name=name,
                company=company,
                phone=f"+1-555-{1000 + i:04d}",
            )
            for i, (name, company) in enumerate(
                [
                    ("Alice Nguyen", "Northwind"),
                    ("Bob Sanchez", "Contoso"),
                    ("Carol Patel", "Fabrikam"),
                    ("David Kim", "Initech"),
                    ("Eve Larsson", "Globex"),
                    ("Frank Osei", "Umbrella"),
                    ("Grace Müller", "Stark Industries"),
                    ("Hassan Ali", "Wayne Enterprises"),
                    ("Ivy Chen", "Soylent"),
                    ("Jack O'Connor", "Cyberdyne"),
                ],
                start=1,
            )
        ],
    ]
    session.add_all(customers)
    await session.flush()

    # --- Demo customer user ---
    # The email must match the Customer record above so the ticket access
    # check passes (it compares user.email to ticket.customer.email).
    customer_user = User(
        organization_id=org.id,
        email=DEMO_CUSTOMER_EMAIL,
        full_name="Casey Customer",
        hashed_password=password_hash,
        role=UserRole.CUSTOMER,
    )
    session.add(customer_user)
    await session.flush()

    # --- SLAs ---
    session.add_all(
        [
            SLA(organization_id=org.id, name="Urgent SLA", priority=TicketPriority.URGENT, first_response_minutes=15, resolution_minutes=240),
            SLA(organization_id=org.id, name="High SLA", priority=TicketPriority.HIGH, first_response_minutes=60, resolution_minutes=480),
            SLA(organization_id=org.id, name="Standard SLA", priority=TicketPriority.MEDIUM, first_response_minutes=240, resolution_minutes=1440),
            SLA(organization_id=org.id, name="Low SLA", priority=TicketPriority.LOW, first_response_minutes=480, resolution_minutes=2880),
        ]
    )
    await session.flush()

    # --- Tickets ---
    now = datetime.now(timezone.utc)
    tickets: list[Ticket] = []
    for index, (title, description, status, priority, source) in enumerate(TICKET_TEMPLATES):
        created = now - timedelta(hours=RNG.randint(2, 240))
        resolved = (
            created + timedelta(hours=RNG.randint(1, 72))
            if status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
            else None
        )
        closed = resolved + timedelta(hours=2) if status == TicketStatus.CLOSED else None
        agent = RNG.choice([None, *agents])
        team = RNG.choice([None, team_tier1, team_tier2])
        category = RNG.choice(categories)

        # Tickets 0 and 11 belong to the demo customer — everyone else
        # gets one of the other customers.
        customer = customers[index % len(customers)]

        ticket = Ticket(
            organization_id=org.id,
            customer_id=customer.id,
            assigned_agent_id=agent.id if agent else None,
            team_id=team.id if team else None,
            category_id=category.id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            source=source,
            created_at=created,
            updated_at=resolved or created,
            resolved_at=resolved,
            closed_at=closed,
        )
        tickets.append(ticket)
    session.add_all(tickets)
    await session.flush()

    # --- Ticket comments + assignment history ---
    for ticket in tickets:
        if ticket.assigned_agent_id is not None:
            session.add(
                TicketAssignment(
                    organization_id=org.id,
                    ticket_id=ticket.id,
                    assigned_to_user_id=ticket.assigned_agent_id,
                    assigned_to_team_id=ticket.team_id,
                    assigned_by_user_id=admin.id,
                    note="Auto-assigned by routing rules.",
                )
            )
        session.add(
            TicketComment(
                organization_id=org.id,
                ticket_id=ticket.id,
                author_user_id=admin.id,
                body="Thanks for reaching out — we're looking into this now.",
                is_internal=False,
            )
        )
        if RNG.random() < 0.6:
            session.add(
                TicketComment(
                    organization_id=org.id,
                    ticket_id=ticket.id,
                    author_user_id=RNG.choice(agents).id,
                    body="Reproduced locally. Escalating to Tier 2 if needed.",
                    is_internal=True,
                )
            )
    await session.flush()

    # --- Knowledge base ---
    kb_categories = [
        KnowledgeBaseCategory(organization_id=org.id, name="Getting Started", description="Onboarding and setup."),
        KnowledgeBaseCategory(organization_id=org.id, name="Billing & Plans", description="Invoices, upgrades, refunds."),
        KnowledgeBaseCategory(organization_id=org.id, name="Troubleshooting", description="Common errors and fixes."),
    ]
    session.add_all(kb_categories)
    await session.flush()

    articles = [
        ("Welcome to SmartDesk AI", "welcome-to-smartdesk-ai", kb_categories[0], ArticleStatus.PUBLISHED),
        ("Inviting teammates and managing roles", "inviting-teammates", kb_categories[0], ArticleStatus.PUBLISHED),
        ("Understanding your invoice", "understanding-your-invoice", kb_categories[1], ArticleStatus.PUBLISHED),
        ("Updating payment methods", "updating-payment-methods", kb_categories[1], ArticleStatus.PUBLISHED),
        ("Resetting a forgotten password", "resetting-forgotten-password", kb_categories[2], ArticleStatus.PUBLISHED),
        ("Debugging webhook signature failures", "debugging-webhook-signatures", kb_categories[2], ArticleStatus.DRAFT),
    ]
    for title, slug, category, status in articles:
        session.add(
            KnowledgeBaseArticle(
                organization_id=org.id,
                category_id=category.id,
                author_user_id=admin.id,
                title=title,
                slug=slug,
                body=f"# {title}\n\nThis is seeded demo content for the SmartDesk AI knowledge base.",
                status=status,
                published_at=now if status == ArticleStatus.PUBLISHED else None,
            )
        )

    # --- Notifications for admin ---
    for ticket in tickets[:5]:
        session.add(
            Notification(
                organization_id=org.id,
                user_id=admin.id,
                type=NotificationType.TICKET_ASSIGNED,
                title=f"Ticket assigned: {ticket.title}",
                body="A ticket has been routed to your team.",
                entity_type="ticket",
                entity_id=ticket.id,
            )
        )

    # --- Audit log entries ---
    session.add_all(
        [
            AuditLog(
                organization_id=org.id,
                actor_user_id=admin.id,
                action="organization.created",
                entity_type="organization",
                entity_id=org.id,
                changes={"name": org.name, "slug": org.slug},
            ),
            AuditLog(
                organization_id=org.id,
                actor_user_id=admin.id,
                action="ticket.seeded",
                entity_type="ticket",
                entity_id=tickets[0].id,
                changes={"count": len(tickets)},
            ),
        ]
    )

    await session.flush()


async def main() -> None:
    async with SessionLocal() as session:
        await seed(session)
        await session.commit()
    await dispose_engine()
    print(f"Seeded organization '{DEMO_ORG_SLUG}' with demo data.")
    print()
    print("Demo accounts (password: Demo123! for all):")
    print("  Admin    → admin@smartdesk-demo.dev")
    print("  Agent    → agent1@smartdesk-demo.dev")
    print("  Customer → customer@smartdesk-demo.dev")


if __name__ == "__main__":
    asyncio.run(main())