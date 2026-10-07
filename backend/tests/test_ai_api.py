"""End-to-end AI endpoint tests using the mock provider."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import AITimeoutError
from app.ai.providers.mock_provider import MockProvider
from app.ai.schemas import (
    ClassificationResult,
    NextActionResult,
    PriorityResult,
    SuggestedResponseResult,
    SummaryResult,
)
from app.ai.schemas import NextAction
from app.core.security import create_access_token
from app.models import (
    AIJob,
    AIJobStatus,
    Customer,
    Organization,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.core.security import hash_password
from tests.ai_fixtures import ai_client  # noqa: F401 -- pytest fixture

pytestmark = pytest.mark.asyncio


async def _tenant(session: AsyncSession, *, slug: str = "acme"):
    org = Organization(name="Acme", slug=slug)
    session.add(org)
    await session.flush()

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
        full_name="Cust",
    )
    session.add_all([agent, customer])
    await session.flush()

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        title="Payment failed twice",
        description="I was charged two times.",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
    )
    session.add(ticket)
    await session.flush()
    token, _ = create_access_token(agent.id)
    return org, agent, ticket, {"Authorization": f"Bearer {token}"}


async def test_classify_endpoint(
    ai_client, db: AsyncSession
) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, _, ticket, headers = await _tenant(db)

    provider.set_response(
        ClassificationResult,
        ClassificationResult(
            category_name="Billing",
            confidence=0.88,
            reasoning_summary="Duplicate charge report.",
        ),
    )

    r = await client.post(
        f"/api/v1/ai/tickets/{ticket.id}/classify", headers=headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "CLASSIFICATION"
    assert body["status"] == "PENDING"
    assert body["payload"]["category_name"] == "Billing"
    assert body["confidence"] == pytest.approx(0.88)


async def test_priority_endpoint(ai_client, db: AsyncSession) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, _, ticket, headers = await _tenant(db)

    provider.set_response(
        PriorityResult,
        PriorityResult(
            suggested_priority=TicketPriority.HIGH,
            confidence=0.72,
            reasoning_summary="Billing issue affecting payment.",
        ),
    )

    r = await client.post(
        f"/api/v1/ai/tickets/{ticket.id}/suggest-priority", headers=headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["payload"]["suggested_priority"] == "HIGH"


async def test_summarize_endpoint(ai_client, db: AsyncSession) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, _, ticket, headers = await _tenant(db)

    provider.set_response(
        SummaryResult,
        SummaryResult(
            summary="Customer reports a duplicate charge.",
            key_points=["Duplicate charge", "No workaround"],
            customer_sentiment="frustrated",
        ),
    )

    r = await client.post(
        f"/api/v1/ai/tickets/{ticket.id}/summarize", headers=headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["payload"]["key_points"] == ["Duplicate charge", "No workaround"]


async def test_suggest_response_endpoint(
    ai_client, db: AsyncSession
) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, _, ticket, headers = await _tenant(db)

    provider.set_response(
        SuggestedResponseResult,
        SuggestedResponseResult(
            draft="Hi Cust, we're looking into the duplicate charge.",
        ),
    )

    r = await client.post(
        f"/api/v1/ai/tickets/{ticket.id}/suggest-response", headers=headers
    )
    assert r.status_code == 200, r.text
    assert "duplicate charge" in r.json()["payload"]["draft"]


async def test_next_action_endpoint(
    ai_client, db: AsyncSession
) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, _, ticket, headers = await _tenant(db)

    provider.set_response(
        NextActionResult,
        NextActionResult(
            action=NextAction.PROVIDE_SOLUTION,
            confidence=0.6,
            reasoning_summary="Refund is appropriate.",
        ),
    )

    r = await client.post(
        f"/api/v1/ai/tickets/{ticket.id}/suggest-next-action", headers=headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["payload"]["action"] == "provide_solution"


async def test_accept_endpoint(ai_client, db: AsyncSession) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, agent, ticket, headers = await _tenant(db)
    provider.set_response(
        ClassificationResult,
        ClassificationResult(
            category_name="Billing", confidence=0.9, reasoning_summary="x"
        ),
    )
    r = await client.post(
        f"/api/v1/ai/tickets/{ticket.id}/classify", headers=headers
    )
    sid = r.json()["id"]

    r2 = await client.post(
        f"/api/v1/ai/suggestions/{sid}/accept", headers=headers
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["suggestion"]["status"] == "ACCEPTED"
    assert r2.json()["suggestion"]["accepted_at"] is not None


async def test_reject_endpoint(ai_client, db: AsyncSession) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, _, ticket, headers = await _tenant(db)
    provider.set_response(
        ClassificationResult,
        ClassificationResult(
            category_name="Billing", confidence=0.9, reasoning_summary="x"
        ),
    )
    r = await client.post(
        f"/api/v1/ai/tickets/{ticket.id}/classify", headers=headers
    )
    sid = r.json()["id"]

    r2 = await client.post(
        f"/api/v1/ai/suggestions/{sid}/reject",
        json={"reason": "Wrong category."},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["suggestion"]["status"] == "REJECTED"
    assert r2.json()["suggestion"]["rejection_reason"] == "Wrong category."


async def test_list_suggestions(ai_client, db: AsyncSession) -> None:  # noqa: ANN001
    client, provider = ai_client
    _, _, ticket, headers = await _tenant(db)
    provider.set_response(
        ClassificationResult,
        ClassificationResult(
            category_name="Billing", confidence=0.9, reasoning_summary="x"
        ),
    )
    await client.post(f"/api/v1/ai/tickets/{ticket.id}/classify", headers=headers)
    await client.post(f"/api/v1/ai/tickets/{ticket.id}/classify", headers=headers)

    r = await client.get(
        f"/api/v1/ai/tickets/{ticket.id}/suggestions", headers=headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 2


async def test_unauthenticated_returns_401(ai_client) -> None:  # noqa: ANN001
    client, _ = ai_client
    r = await client.post(f"/api/v1/ai/tickets/{uuid.uuid4()}/classify")
    assert r.status_code == 401


async def test_cross_tenant_classify_returns_404(
    ai_client, db: AsyncSession
) -> None:  # noqa: ANN001
    client, _ = ai_client
    _, _, ticket_a, _ = await _tenant(db, slug="tenant-a")
    _, _, _, headers_b = await _tenant(db, slug="tenant-b")

    r = await client.post(
        f"/api/v1/ai/tickets/{ticket_a.id}/classify", headers=headers_b
    )
    assert r.status_code == 404


async def test_provider_timeout_returns_504(
    db: AsyncSession, mock_provider: MockProvider
) -> None:
    """Override the shared fixture to inject a failing provider, then
    assert the endpoint maps the failure to 504 and records a TIMEOUT job."""
    from httpx import ASGITransport, AsyncClient

    from app.ai.factory import get_ai_service
    from app.ai.service import AIService
    from app.db.session import get_db
    from app.main import app as fastapi_app

    _, _, ticket, headers = await _tenant(db)

    failing = MockProvider(fail_with=AITimeoutError())

    async def override_get_db():
        yield db

    def override_ai_service() -> AIService:
        return AIService(db=db, provider=failing)

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_ai_service] = override_ai_service
    try:
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/ai/tickets/{ticket.id}/classify", headers=headers
            )
        assert r.status_code == 504
        assert r.json()["error"]["code"] == "ai_timeout"

        job = await db.scalar(
            select(AIJob).where(AIJob.ticket_id == ticket.id)
        )
        assert job is not None
        assert job.status == AIJobStatus.TIMEOUT
    finally:
        fastapi_app.dependency_overrides.clear()