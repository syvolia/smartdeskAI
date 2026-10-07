"""AI service tests. All AI calls are served by the MockProvider."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import AITimeoutError, AIUnavailableError
from app.ai.providers.mock_provider import MockProvider
from app.ai.schemas import (
    ClassificationResult,
    NextAction,
    NextActionResult,
    PriorityResult,
    ResponseTone,
    SuggestedResponseResult,
    SummaryResult,
)
from app.ai.service import AIService
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models import (
    AIJob,
    AIJobStatus,
    AISuggestion,
    AISuggestionKind,
    AISuggestionStatus,
    Customer,
    Organization,
    SLA,
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


async def _bootstrap(session: AsyncSession, *, slug: str = "acme"):
    org = Organization(name="Acme", slug=slug)
    session.add(org)
    await session.flush()

    admin = User(
        organization_id=org.id,
        email=f"admin-{slug}@ex.test",
        full_name="Ada Admin",
        hashed_password=hash_password("pw"),
        role=UserRole.ADMIN,
    )
    agent = User(
        organization_id=org.id,
        email=f"agent-{slug}@ex.test",
        full_name="Grace Agent",
        hashed_password=hash_password("pw"),
        role=UserRole.AGENT,
    )
    customer = Customer(
        organization_id=org.id,
        email=f"cust-{slug}@ex.test",
        full_name="Cust One",
    )
    category = TicketCategory(organization_id=org.id, name="Billing")
    session.add_all([admin, agent, customer, category])
    await session.flush()

    sla = SLA(
        organization_id=org.id,
        name="Standard",
        priority=TicketPriority.MEDIUM,
        first_response_minutes=60,
        resolution_minutes=480,
    )
    session.add(sla)
    await session.flush()

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        title="Cannot log in",
        description="I get an error every time.",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        category_id=category.id,
    )
    session.add(ticket)
    await session.flush()

    return org, admin, agent, customer, ticket


async def test_classify_returns_persisted_suggestion(db: AsyncSession) -> None:
    org, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider()
    provider.set_response(
        ClassificationResult,
        ClassificationResult(
            category_name="Billing",
            confidence=0.91,
            reasoning_summary="Mentions login errors tied to a billing change.",
        ),
    )

    service = AIService(db=db, provider=provider)
    suggestion = await service.classify(ticket.id, admin)

    assert suggestion.kind == AISuggestionKind.CLASSIFICATION
    assert suggestion.status == AISuggestionStatus.PENDING
    assert suggestion.organization_id == org.id
    assert suggestion.ticket_id == ticket.id
    assert suggestion.payload["category_name"] == "Billing"
    assert suggestion.confidence == pytest.approx(0.91)

    # Job was recorded.
    job = await db.scalar(select(AIJob).where(AIJob.ticket_id == ticket.id))
    assert job is not None
    assert job.status == AIJobStatus.SUCCESS
    assert job.input_tokens == 128
    assert job.output_tokens == 64


async def test_suggest_priority(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider()
    provider.set_response(
        PriorityResult,
        PriorityResult(
            suggested_priority=TicketPriority.HIGH,
            confidence=0.77,
            reasoning_summary="Production login outage for multiple users.",
        ),
    )
    service = AIService(db=db, provider=provider)
    suggestion = await service.suggest_priority(ticket.id, admin)

    assert suggestion.kind == AISuggestionKind.PRIORITY
    assert suggestion.payload["suggested_priority"] == "HIGH"


async def test_summarize(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider()
    provider.set_response(
        SummaryResult,
        SummaryResult(
            summary="Customer cannot log in and is blocked.",
            key_points=["Login fails", "No workaround offered"],
            customer_sentiment="frustrated",
        ),
    )
    service = AIService(db=db, provider=provider)
    suggestion = await service.summarize(ticket.id, admin)

    assert suggestion.kind == AISuggestionKind.SUMMARY
    assert suggestion.payload["customer_sentiment"] == "frustrated"


async def test_suggest_response(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider()
    provider.set_response(
        SuggestedResponseResult,
        SuggestedResponseResult(
            draft="Hi Cust, thanks for reaching out — we're looking into this.",
            tone=ResponseTone.FRIENDLY,
            cited_article_ids=[],
        ),
    )
    service = AIService(db=db, provider=provider)
    suggestion = await service.suggest_response(ticket.id, admin)

    assert suggestion.kind == AISuggestionKind.SUGGESTED_RESPONSE
    assert "we're looking" in suggestion.payload["draft"]


async def test_suggest_next_action(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider()
    provider.set_response(
        NextActionResult,
        NextActionResult(
            action=NextAction.REQUEST_INFORMATION,
            confidence=0.65,
            reasoning_summary="Need browser and OS details.",
        ),
    )
    service = AIService(db=db, provider=provider)
    suggestion = await service.suggest_next_action(ticket.id, admin)

    assert suggestion.kind == AISuggestionKind.NEXT_ACTION
    assert suggestion.payload["action"] == "request_information"


async def test_accept_and_reject(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider()
    provider.set_response(
        ClassificationResult,
        ClassificationResult(
            category_name="Billing", confidence=0.9, reasoning_summary="x"
        ),
    )
    service = AIService(db=db, provider=provider)

    s1 = await service.classify(ticket.id, admin)
    accepted = await service.accept(s1.id, admin)
    assert accepted.status == AISuggestionStatus.ACCEPTED
    assert accepted.accepted_by_user_id == admin.id

    s2 = await service.classify(ticket.id, admin)
    rejected = await service.reject(s2.id, admin, reason="Wrong category.")
    assert rejected.status == AISuggestionStatus.REJECTED
    assert rejected.rejection_reason == "Wrong category."

    # Accepting s1 superseded s2? No — s2 was already rejected. Verify
    # that generating another pending suggestion then accepting it
    # supersedes the older pending one.
    s3 = await service.classify(ticket.id, admin)
    s4 = await service.classify(ticket.id, admin)
    accepted4 = await service.accept(s4.id, admin)
    assert accepted4.status == AISuggestionStatus.ACCEPTED

    refreshed_s3 = await db.get(AISuggestion, s3.id)
    assert refreshed_s3 is not None
    assert refreshed_s3.status == AISuggestionStatus.SUPERSEDED


async def test_provider_timeout_is_recorded(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider(fail_with=AITimeoutError())
    service = AIService(db=db, provider=provider)

    with pytest.raises(AITimeoutError):
        await service.classify(ticket.id, admin)

    job = await db.scalar(select(AIJob).where(AIJob.ticket_id == ticket.id))
    assert job is not None
    assert job.status == AIJobStatus.TIMEOUT


async def test_provider_failure_is_recorded(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)

    provider = MockProvider(fail_with=AIUnavailableError())
    service = AIService(db=db, provider=provider)

    with pytest.raises(AIUnavailableError):
        await service.suggest_priority(ticket.id, admin)

    job = await db.scalar(select(AIJob).where(AIJob.ticket_id == ticket.id))
    assert job is not None
    assert job.status == AIJobStatus.FAILED


async def test_customer_cannot_use_ai(db: AsyncSession) -> None:
    _, _, _, customer, ticket = await _bootstrap(db)

    customer_user = User(
        organization_id=ticket.organization_id,
        email=customer.email,
        full_name=customer.full_name,
        hashed_password=hash_password("pw"),
        role=UserRole.CUSTOMER,
    )
    db.add(customer_user)
    await db.flush()

    service = AIService(db=db, provider=MockProvider())
    with pytest.raises(ForbiddenError):
        await service.classify(ticket.id, customer_user)


async def test_cross_tenant_isolation(db: AsyncSession) -> None:
    _, _, _, _, ticket_a = await _bootstrap(db, slug="tenant-a")
    _, admin_b, _, _, _ = await _bootstrap(db, slug="tenant-b")

    service = AIService(db=db, provider=MockProvider())
    with pytest.raises(NotFoundError):
        await service.classify(ticket_a.id, admin_b)


async def test_list_for_ticket_is_tenant_scoped(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)
    provider = MockProvider()
    provider.set_response(
        ClassificationResult,
        ClassificationResult(category_name="Billing", confidence=0.9, reasoning_summary="x"),
    )
    service = AIService(db=db, provider=provider)
    await service.classify(ticket.id, admin)
    await service.classify(ticket.id, admin)

    items = await service.list_for_ticket(ticket.id, admin)
    assert len(items) == 2


async def test_prompt_contains_ticket_context(db: AsyncSession) -> None:
    _, admin, _, _, ticket = await _bootstrap(db)
    provider = MockProvider()
    provider.set_response(
        ClassificationResult,
        ClassificationResult(category_name="Billing", confidence=0.9, reasoning_summary="x"),
    )
    service = AIService(db=db, provider=provider)
    await service.classify(ticket.id, admin)

    assert provider.calls, "provider should have been called"
    call = provider.calls[0]
    assert call["schema"] == "ClassificationResult"
    assert ticket.title in call["user"]
    assert "Billing" in call["user"]  # category list is passed in