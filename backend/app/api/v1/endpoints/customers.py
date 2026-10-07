"""Customer endpoints.

Reads available to staff (admin or agent). Customers don't get direct
access to the full directory — they only see themselves via /auth/me.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models import Customer, User, UserRole
from app.schemas.customer import (
    CustomerCreateRequest,
    CustomerListResponse,
    CustomerResponse,
)

router = APIRouter(prefix="/customers", tags=["customers"])


def _require_staff(user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.AGENT):
        raise ForbiddenError("Staff access required.")


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Administrator access required.")


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List customers in the organization.",
)
async def list_customers(
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerListResponse:
    _require_staff(user)

    base = select(Customer).where(Customer.organization_id == user.organization_id)
    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                Customer.full_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.company.ilike(pattern),
            )
        )

    total = int(
        await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    )

    stmt = (
        base.order_by(Customer.full_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list((await db.scalars(stmt)).all())
    pages = (total + page_size - 1) // page_size if page_size else 0

    return CustomerListResponse(
        items=[CustomerResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get a customer by id.",
)
async def get_customer(
    customer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    _require_staff(user)
    customer = await db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == user.organization_id,
        )
    )
    if customer is None:
        raise NotFoundError("Customer not found.")
    return CustomerResponse.model_validate(customer)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer (admin only).",
)
async def create_customer(
    payload: CustomerCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    _require_admin(user)

    existing = await db.scalar(
        select(Customer).where(
            Customer.organization_id == user.organization_id,
            Customer.email == payload.email,
        )
    )
    if existing is not None:
        raise ConflictError("A customer with this email already exists.")

    customer = Customer(
        organization_id=user.organization_id,
        email=payload.email,
        full_name=payload.full_name,
        company=payload.company,
        phone=payload.phone,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)