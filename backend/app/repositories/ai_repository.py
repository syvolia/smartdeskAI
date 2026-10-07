"""Data access for AI jobs and suggestions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AIJob,
    AIJobStatus,
    AIOperation,
    AISuggestion,
    AISuggestionKind,
    AISuggestionStatus,
)


class AIRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- jobs ----------

    async def create_job(
        self,
        *,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        operation: AIOperation,
        status: AIJobStatus,
        provider: str,
        model: str,
        prompt_hash: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        latency_ms: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> AIJob:
        job = AIJob(
            organization_id=organization_id,
            ticket_id=ticket_id,
            user_id=user_id,
            operation=operation,
            status=status,
            provider=provider,
            model=model,
            prompt_hash=prompt_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            error_code=error_code,
            error_message=error_message,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    # ---------- suggestions ----------

    async def create_suggestion(
        self,
        *,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        job_id: uuid.UUID | None,
        kind: AISuggestionKind,
        payload: dict,
        confidence: float | None,
        model: str,
    ) -> AISuggestion:
        suggestion = AISuggestion(
            organization_id=organization_id,
            ticket_id=ticket_id,
            job_id=job_id,
            kind=kind,
            status=AISuggestionStatus.PENDING,
            payload=payload,
            confidence=confidence,
            model=model,
        )
        self.db.add(suggestion)
        await self.db.flush()
        return suggestion

    async def get_suggestion(
        self, suggestion_id: uuid.UUID, org_id: uuid.UUID
    ) -> AISuggestion | None:
        return await self.db.scalar(
            select(AISuggestion).where(
                AISuggestion.id == suggestion_id,
                AISuggestion.organization_id == org_id,
            )
        )

    async def list_for_ticket(
        self,
        ticket_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        kind: AISuggestionKind | None = None,
        limit: int = 50,
    ) -> list[AISuggestion]:
        stmt = (
            select(AISuggestion)
            .where(
                AISuggestion.ticket_id == ticket_id,
                AISuggestion.organization_id == org_id,
            )
            .order_by(AISuggestion.created_at.desc())
            .limit(limit)
        )
        if kind is not None:
            stmt = stmt.where(AISuggestion.kind == kind)
        return list((await self.db.scalars(stmt)).all())

    async def supersede_pending(
        self,
        *,
        ticket_id: uuid.UUID,
        org_id: uuid.UUID,
        kind: AISuggestionKind,
        keep_id: uuid.UUID,
    ) -> int:
        stmt = (
            update(AISuggestion)
            .where(
                AISuggestion.ticket_id == ticket_id,
                AISuggestion.organization_id == org_id,
                AISuggestion.kind == kind,
                AISuggestion.status == AISuggestionStatus.PENDING,
                AISuggestion.id != keep_id,
            )
            .values(status=AISuggestionStatus.SUPERSEDED)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount or 0

    async def accept(
        self, suggestion: AISuggestion, user_id: uuid.UUID
    ) -> None:
        suggestion.status = AISuggestionStatus.ACCEPTED
        suggestion.accepted_by_user_id = user_id
        suggestion.accepted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def reject(
        self,
        suggestion: AISuggestion,
        user_id: uuid.UUID,
        reason: str | None,
    ) -> None:
        suggestion.status = AISuggestionStatus.REJECTED
        suggestion.rejected_by_user_id = user_id
        suggestion.rejected_at = datetime.now(timezone.utc)
        suggestion.rejection_reason = reason
        await self.db.flush()

    # ---------- metrics helpers ----------

    async def count_for_org(
        self,
        org_id: uuid.UUID,
        *,
        kind: AISuggestionKind | None = None,
        status: AISuggestionStatus | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(AISuggestion).where(
            AISuggestion.organization_id == org_id
        )
        if kind is not None:
            stmt = stmt.where(AISuggestion.kind == kind)
        if status is not None:
            stmt = stmt.where(AISuggestion.status == status)
        return int(await self.db.scalar(stmt) or 0)