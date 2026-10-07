"""AI orchestration service.

All AI behavior lives behind this class. Routers call it; it never calls
OpenAI directly (the provider abstraction does). It loads tenant-scoped
data, builds prompts, validates outputs, and persists jobs and suggestions.

The AI never mutates a ticket. It only produces suggestions with an
acceptance lifecycle for later analytics.
"""

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import AIUnavailableError
from app.ai.prompts import (
    SYSTEM_CLASSIFIER,
    SYSTEM_NEXT_ACTION,
    SYSTEM_PRIORITY,
    SYSTEM_RESPONDER,
    SYSTEM_SUMMARIZER,
    user_classify,
    user_next_action,
    user_priority,
    user_respond,
    user_summarize,
)
from app.ai.provider import LLMProvider, LLMMetadata
from app.ai.schemas import (
    ClassificationResult,
    NextActionResult,
    PriorityResult,
    SuggestedResponseResult,
    SummaryResult,
)
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models import (
    AIJobStatus,
    AIOperation,
    AISuggestion,
    AISuggestionKind,
    KnowledgeBaseArticle,
    Ticket,
    TicketComment,
    User,
    UserRole,
)
from app.repositories.ai_repository import AIRepository
from app.repositories.ticket_repository import TicketRepository

logger = get_logger(__name__)


@dataclass
class _RunContext:
    ticket: Ticket
    comments: list[TicketComment]
    categories: list[str]
    kb_articles: list[tuple[str, str, str]]


class AIService:
    def __init__(self, db: AsyncSession, provider: LLMProvider) -> None:
        self.db = db
        self.provider = provider
        self.tickets = TicketRepository(db)
        self.repo = AIRepository(db)

    # ---------- public API ----------

    async def classify(
        self, ticket_id: uuid.UUID, user: User
    ) -> AISuggestion:
        ctx = await self._load_context(ticket_id, user)
        result, meta = await self._run(
            user=user,
            ticket=ctx.ticket,
            operation=AIOperation.CLASSIFY,
            kind=AISuggestionKind.CLASSIFICATION,
            system=SYSTEM_CLASSIFIER,
            user_prompt=user_classify(ctx.ticket, ctx.categories),
            schema=ClassificationResult,
        )

        payload = result.model_dump(mode="json")

        # Resolve the category name to an id so the frontend can apply it
        # via PATCH /tickets/{id} without an extra categories endpoint.
        from app.models import TicketCategory

        category = await self.db.scalar(
            select(TicketCategory).where(
                TicketCategory.organization_id == user.organization_id,
                TicketCategory.name == result.category_name,
            )
        )
        payload["category_id"] = str(category.id) if category else None

        return await self._persist(
            user,
            ctx.ticket,
            meta,
            kind=AISuggestionKind.CLASSIFICATION,
            operation=AIOperation.CLASSIFY,
            payload=payload,
            confidence=result.confidence,
        )

    async def suggest_priority(
        self, ticket_id: uuid.UUID, user: User
    ) -> AISuggestion:
        ctx = await self._load_context(ticket_id, user)
        result, meta = await self._run(
            user=user,
            ticket=ctx.ticket,
            operation=AIOperation.SUGGEST_PRIORITY,
            kind=AISuggestionKind.PRIORITY,
            system=SYSTEM_PRIORITY,
            user_prompt=user_priority(ctx.ticket),
            schema=PriorityResult,
        )
        payload = result.model_dump(mode="json")
        return await self._persist(user, ctx.ticket, meta, kind=AISuggestionKind.PRIORITY,
                                   operation=AIOperation.SUGGEST_PRIORITY,
                                   payload=payload, confidence=result.confidence)

    async def summarize(
        self, ticket_id: uuid.UUID, user: User
    ) -> AISuggestion:
        ctx = await self._load_context(ticket_id, user)
        result, meta = await self._run(
            user=user,
            ticket=ctx.ticket,
            operation=AIOperation.SUMMARIZE,
            kind=AISuggestionKind.SUMMARY,
            system=SYSTEM_SUMMARIZER,
            user_prompt=user_summarize(ctx.ticket, ctx.comments),
            schema=SummaryResult,
        )
        payload = result.model_dump(mode="json")
        return await self._persist(user, ctx.ticket, meta, kind=AISuggestionKind.SUMMARY,
                                   operation=AIOperation.SUMMARIZE,
                                   payload=payload, confidence=None)

    async def suggest_response(
        self, ticket_id: uuid.UUID, user: User
    ) -> AISuggestion:
        ctx = await self._load_context(ticket_id, user)
        result, meta = await self._run(
            user=user,
            ticket=ctx.ticket,
            operation=AIOperation.SUGGEST_RESPONSE,
            kind=AISuggestionKind.SUGGESTED_RESPONSE,
            system=SYSTEM_RESPONDER,
            user_prompt=user_respond(ctx.ticket, ctx.comments, ctx.kb_articles),
            schema=SuggestedResponseResult,
        )

        payload = result.model_dump(mode="json")

        # Enrich cited ids with the title/excerpt we already retrieved, so
        # the frontend can render the "sources" list without another fetch.
        articles_by_id = {
            article_id: (title, excerpt)
            for article_id, title, excerpt in ctx.kb_articles
        }
        payload["cited_articles"] = [
            {
                "id": article_id,
                "title": articles_by_id[article_id][0],
                "excerpt": articles_by_id[article_id][1],
            }
            for article_id in result.cited_article_ids
            if article_id in articles_by_id
        ]

        return await self._persist(
            user,
            ctx.ticket,
            meta,
            kind=AISuggestionKind.SUGGESTED_RESPONSE,
            operation=AIOperation.SUGGEST_RESPONSE,
            payload=payload,
            confidence=None,
        )

    async def suggest_next_action(
        self, ticket_id: uuid.UUID, user: User
    ) -> AISuggestion:
        ctx = await self._load_context(ticket_id, user)
        result, meta = await self._run(
            user=user,
            ticket=ctx.ticket,
            operation=AIOperation.SUGGEST_NEXT_ACTION,
            kind=AISuggestionKind.NEXT_ACTION,
            system=SYSTEM_NEXT_ACTION,
            user_prompt=user_next_action(ctx.ticket, ctx.comments),
            schema=NextActionResult,
        )
        payload = result.model_dump(mode="json")
        return await self._persist(user, ctx.ticket, meta,
                                   kind=AISuggestionKind.NEXT_ACTION,
                                   operation=AIOperation.SUGGEST_NEXT_ACTION,
                                   payload=payload, confidence=result.confidence)

    async def accept(
        self,
        suggestion_id: uuid.UUID,
        user: User,
        *,
        supersede_previous: bool = True,
    ) -> AISuggestion:
        self._require_staff(user)
        suggestion = await self.repo.get_suggestion(
            suggestion_id, user.organization_id
        )
        if suggestion is None:
            raise NotFoundError("Suggestion not found.")

        await self.repo.accept(suggestion, user.id)

        if supersede_previous:
            await self.repo.supersede_pending(
                ticket_id=suggestion.ticket_id,
                org_id=suggestion.organization_id,
                kind=suggestion.kind,
                keep_id=suggestion.id,
            )

        logger.info(
            "ai_suggestion_accepted",
            suggestion_id=str(suggestion.id),
            ticket_id=str(suggestion.ticket_id),
            org_id=str(suggestion.organization_id),
            kind=suggestion.kind.value,
            user_id=str(user.id),
        )
        return suggestion

    async def reject(
        self,
        suggestion_id: uuid.UUID,
        user: User,
        reason: str | None,
    ) -> AISuggestion:
        self._require_staff(user)
        suggestion = await self.repo.get_suggestion(
            suggestion_id, user.organization_id
        )
        if suggestion is None:
            raise NotFoundError("Suggestion not found.")

        await self.repo.reject(suggestion, user.id, reason)
        logger.info(
            "ai_suggestion_rejected",
            suggestion_id=str(suggestion.id),
            ticket_id=str(suggestion.ticket_id),
            org_id=str(suggestion.organization_id),
            kind=suggestion.kind.value,
            user_id=str(user.id),
        )
        return suggestion

    async def list_for_ticket(
        self,
        ticket_id: uuid.UUID,
        user: User,
        *,
        kind: AISuggestionKind | None = None,
    ) -> list[AISuggestion]:
        # Ensures the ticket exists in this tenant before listing.
        ticket = await self.tickets.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        self._require_read_access(ticket, user)
        return await self.repo.list_for_ticket(
            ticket_id, user.organization_id, kind=kind
        )

    # ---------- internals ----------

    @staticmethod
    def _is_staff(user: User) -> bool:
        return user.role in (UserRole.ADMIN, UserRole.AGENT)

    def _require_staff(self, user: User) -> None:
        if not self._is_staff(user):
            raise ForbiddenError("Only agents can use the AI copilot.")

    def _require_read_access(self, ticket: Ticket, user: User) -> None:
        if self._is_staff(user):
            return
        if ticket.customer.email != user.email:
            raise NotFoundError("Ticket not found.")

    async def _load_context(
        self, ticket_id: uuid.UUID, user: User
    ) -> _RunContext:
        self._require_staff(user)

        ticket = await self.tickets.get(ticket_id, user.organization_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")

        comments = list(
            (
                await self.db.scalars(
                    select(TicketComment)
                    .where(
                        TicketComment.ticket_id == ticket.id,
                        TicketComment.organization_id == user.organization_id,
                    )
                    .order_by(TicketComment.created_at.asc())
                )
            ).all()
        )

        # Category names for classification.
        from app.models import TicketCategory

        category_names = list(
            (
                await self.db.scalars(
                    select(TicketCategory.name)
                    .where(
                        TicketCategory.organization_id == user.organization_id
                    )
                    .order_by(TicketCategory.name.asc())
                )
            ).all()
        )

        # Very lightweight KB lookup. Phase 8 replaces this with vector search.
        kb_articles = await self._find_kb_articles(ticket, user)

        return _RunContext(
            ticket=ticket,
            comments=comments,
            categories=category_names,
            kb_articles=kb_articles,
        )

    async def _find_kb_articles(
        self, ticket: Ticket, user: User
    ) -> list[tuple[str, str, str]]:
        # ILIKE on title using the first few significant words of the title.
        words = [w for w in ticket.title.split() if len(w) > 3][:4]
        if not words:
            return []
        pattern = f"%{words[0]}%"
        rows = list(
            (
                await self.db.scalars(
                    select(KnowledgeBaseArticle)
                    .where(
                        KnowledgeBaseArticle.organization_id == user.organization_id,
                        KnowledgeBaseArticle.title.ilike(pattern),
                    )
                    .limit(3)
                )
            ).all()
        )
        return [
            (str(a.id), a.title, a.body[:400].replace("\n", " "))
            for a in rows
        ]

    async def _run(
        self,
        *,
        user: User,
        ticket: Ticket,
        operation: AIOperation,
        kind: AISuggestionKind,
        system: str,
        user_prompt: str,
        schema,
    ):
        prompt_hash = hashlib.sha256(
            f"{system}\n---\n{user_prompt}".encode("utf-8")
        ).hexdigest()[:32]

        try:
            result, meta = await self.provider.complete_json(
                system=system,
                user=user_prompt,
                schema=schema,
                timeout_seconds=settings.openai_timeout_seconds,
            )
        except AIUnavailableError as exc:
            await self._record_failure(
                user=user, ticket=ticket, operation=operation,
                provider_name=getattr(self.provider, "name", "unknown"),
                model=getattr(self.provider, "_model", "unknown"),
                prompt_hash=prompt_hash,
                status=AIJobStatus.FAILED,
                error_code="unavailable",
                error_message=str(exc),
            )
            raise
        except Exception as exc:  # noqa: BLE001 -- we deliberately map everything
            # Providers surface timeouts/invalid responses through typed
            # exceptions; anything else is unexpected. We still record it.
            is_timeout = exc.__class__.__name__ == "AITimeoutError"
            status = AIJobStatus.TIMEOUT if is_timeout else AIJobStatus.FAILED
            await self._record_failure(
                user=user, ticket=ticket, operation=operation,
                provider_name=getattr(self.provider, "name", "unknown"),
                model=getattr(self.provider, "_model", "unknown"),
                prompt_hash=prompt_hash,
                status=status,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
            )
            raise

        logger.info(
            "ai_call_succeeded",
            operation=operation.value,
            kind=kind.value,
            provider=meta.provider,
            model=meta.model,
            latency_ms=meta.latency_ms,
            input_tokens=meta.input_tokens,
            output_tokens=meta.output_tokens,
            prompt_hash=prompt_hash,
            ticket_id=str(ticket.id),
            org_id=str(ticket.organization_id),
            user_id=str(user.id),
        )
        return result, meta

    async def _record_failure(
        self,
        *,
        user: User,
        ticket: Ticket,
        operation: AIOperation,
        provider_name: str,
        model: str,
        prompt_hash: str,
        status: AIJobStatus,
        error_code: str,
        error_message: str,
    ) -> None:
        await self.repo.create_job(
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            user_id=user.id,
            operation=operation,
            status=status,
            provider=provider_name,
            model=model,
            prompt_hash=prompt_hash,
            error_code=error_code,
            error_message=error_message[:500],
        )
        logger.warning(
            "ai_call_failed",
            operation=operation.value,
            status=status.value,
            provider=provider_name,
            model=model,
            error_code=error_code,
            prompt_hash=prompt_hash,
            ticket_id=str(ticket.id),
            org_id=str(ticket.organization_id),
            user_id=str(user.id),
        )

    async def _persist(
        self,
        user: User,
        ticket: Ticket,
        meta: LLMMetadata,
        *,
        kind: AISuggestionKind,
        operation: AIOperation,
        payload: dict,
        confidence: float | None,
    ) -> AISuggestion:
        job = await self.repo.create_job(
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            user_id=user.id,
            operation=operation,
            status=AIJobStatus.SUCCESS,
            provider=meta.provider,
            model=meta.model,
            input_tokens=meta.input_tokens,
            output_tokens=meta.output_tokens,
            latency_ms=meta.latency_ms,
        )
        suggestion = await self.repo.create_suggestion(
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            job_id=job.id,
            kind=kind,
            payload=payload,
            confidence=confidence,
            model=meta.model,
        )
        return suggestion