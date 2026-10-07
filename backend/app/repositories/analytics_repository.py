"""Read-only aggregate queries for analytics.

Each public method maps to one SQL statement (or a small fixed number of
them). No per-row lookups, no ORM lazy loading. Everything is scoped to a
single organization and an optional date range.

Notes on the SQL:
- On LEFT JOINs, use `func.count(column)` — `func.count()` would count the
  outer row itself and report 1 instead of 0.
- Group by unlabeled expressions (`func.coalesce(...)`) rather than
  labeled `.label()` aliases to avoid ambiguous grouping in Postgres.
- Date truncation is passed as a bound parameter to `date_trunc()`,
  which Postgres handles natively.
"""

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AISuggestion,
    AISuggestionStatus,
    Ticket,
    TicketCategory,
    TicketStatus,
    User,
)


def _day_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
    return start, end


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- ticket overview ----------

    async def ticket_overview(
        self,
        org_id: uuid.UUID,
        date_from: date,
        date_to: date,
    ) -> dict:
        start, end = _day_bounds(date_from, date_to)
        status_col = Ticket.status
        priority_col = Ticket.priority

        stmt = select(
            func.count().label("total"),
            func.count().filter(status_col == TicketStatus.OPEN).label("open"),
            func.count()
            .filter(status_col == TicketStatus.IN_PROGRESS)
            .label("in_progress"),
            func.count()
            .filter(status_col == TicketStatus.WAITING_CUSTOMER)
            .label("waiting_customer"),
            func.count()
            .filter(status_col == TicketStatus.RESOLVED)
            .label("resolved"),
            func.count()
            .filter(status_col == TicketStatus.CLOSED)
            .label("closed"),
        ).where(
            Ticket.organization_id == org_id,
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
        row = (await self.db.execute(stmt)).one()

        by_status_stmt = (
            select(status_col.label("status"), func.count().label("value"))
            .where(
                Ticket.organization_id == org_id,
                Ticket.created_at >= start,
                Ticket.created_at <= end,
            )
            .group_by(status_col)
        )
        by_status = [
            {"name": s.value if hasattr(s, "value") else str(s), "value": int(c)}
            for s, c in (await self.db.execute(by_status_stmt)).all()
        ]

        by_priority_stmt = (
            select(priority_col.label("priority"), func.count().label("value"))
            .where(
                Ticket.organization_id == org_id,
                Ticket.created_at >= start,
                Ticket.created_at <= end,
            )
            .group_by(priority_col)
        )
        by_priority = [
            {"name": p.value if hasattr(p, "value") else str(p), "value": int(c)}
            for p, c in (await self.db.execute(by_priority_stmt)).all()
        ]

        # Group by the raw coalesce expression, not its label.
        category_name = func.coalesce(TicketCategory.name, "Uncategorized")
        by_category_stmt = (
            select(category_name.label("name"), func.count().label("value"))
            .select_from(Ticket)
            .outerjoin(TicketCategory, TicketCategory.id == Ticket.category_id)
            .where(
                Ticket.organization_id == org_id,
                Ticket.created_at >= start,
                Ticket.created_at <= end,
            )
            .group_by(category_name)
            .order_by(func.count().desc())
        )
        by_category = [
            {"name": str(name), "value": int(value)}
            for name, value in (await self.db.execute(by_category_stmt)).all()
        ]

        return {
            "total": int(row.total),
            "open": int(row.open),
            "in_progress": int(row.in_progress),
            "waiting_customer": int(row.waiting_customer),
            "resolved": int(row.resolved),
            "closed": int(row.closed),
            "by_status": by_status,
            "by_priority": by_priority,
            "by_category": by_category,
        }

    # ---------- time series ----------

    async def ticket_time_series(
        self,
        org_id: uuid.UUID,
        date_from: date,
        date_to: date,
        *,
        granularity: str,
    ) -> dict:
        start, end = _day_bounds(date_from, date_to)

        # Wrap granularity as a bind parameter; date_trunc accepts it.
        trunc = func.date_trunc(granularity, Ticket.created_at)
        created_stmt = (
            select(trunc.label("bucket"), func.count().label("count"))
            .where(
                Ticket.organization_id == org_id,
                Ticket.created_at >= start,
                Ticket.created_at <= end,
            )
            .group_by(trunc)
            .order_by(trunc)
        )
        created = [
            {"bucket": b, "count": int(c)}
            for b, c in (await self.db.execute(created_stmt)).all()
        ]

        trunc_res = func.date_trunc(granularity, Ticket.resolved_at)
        resolved_stmt = (
            select(trunc_res.label("bucket"), func.count().label("count"))
            .where(
                Ticket.organization_id == org_id,
                Ticket.resolved_at.is_not(None),
                Ticket.resolved_at >= start,
                Ticket.resolved_at <= end,
            )
            .group_by(trunc_res)
            .order_by(trunc_res)
        )
        resolved = [
            {"bucket": b, "count": int(c)}
            for b, c in (await self.db.execute(resolved_stmt)).all()
        ]

        return {"created": created, "resolved": resolved}

    # ---------- SLA ----------

    async def sla_metrics(
        self,
        org_id: uuid.UUID,
        date_from: date,
        date_to: date,
    ) -> dict:
        start, end = _day_bounds(date_from, date_to)

        first_response_seconds = func.extract(
            "epoch",
            Ticket.first_response_at - Ticket.created_at,
        )
        resolution_seconds = func.extract(
            "epoch",
            Ticket.resolved_at - Ticket.created_at,
        )

        stmt = select(
            func.avg(first_response_seconds).label("fr_avg"),
            func.count(first_response_seconds).label("fr_samples"),
            func.avg(resolution_seconds).label("res_avg"),
            func.count(resolution_seconds).label("res_samples"),
            func.count()
            .filter(Ticket.sla_policy_id.is_not(None))
            .label("total_with_sla"),
            func.count()
            .filter(Ticket.sla_breached.is_(True))
            .label("breached"),
        ).where(
            Ticket.organization_id == org_id,
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
        row = (await self.db.execute(stmt)).one()

        total_with_sla = int(row.total_with_sla)
        breached = int(row.breached)
        compliance = (
            (total_with_sla - breached) / total_with_sla * 100
            if total_with_sla > 0
            else 100.0
        )

        return {
            "first_response_avg_seconds": float(row.fr_avg) if row.fr_avg else None,
            "first_response_samples": int(row.fr_samples),
            "resolution_avg_seconds": float(row.res_avg) if row.res_avg else None,
            "resolution_samples": int(row.res_samples),
            "sla_compliance_percentage": round(compliance, 2),
            "breached": breached,
            "total_with_sla": total_with_sla,
        }

    # ---------- agent workload ----------

    async def agent_workload(
        self,
        org_id: uuid.UUID,
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        start, end = _day_bounds(date_from, date_to)
        status_col = Ticket.status

        # Important: count Ticket.id, not * , so LEFT JOIN users with no
        # matching tickets get 0 (not 1).
        join_cond = (
            (Ticket.assigned_agent_id == User.id)
            & (Ticket.organization_id == org_id)
            & (Ticket.created_at >= start)
            & (Ticket.created_at <= end)
        )

        stmt = (
            select(
                User.id.label("agent_id"),
                User.full_name.label("agent_name"),
                func.count(Ticket.id)
                .filter(status_col == TicketStatus.OPEN)
                .label("open"),
                func.count(Ticket.id)
                .filter(status_col == TicketStatus.IN_PROGRESS)
                .label("in_progress"),
                func.count(Ticket.id)
                .filter(status_col == TicketStatus.WAITING_CUSTOMER)
                .label("waiting_customer"),
                func.count(Ticket.id)
                .filter(status_col == TicketStatus.RESOLVED)
                .label("resolved"),
                func.count(Ticket.id)
                .filter(status_col == TicketStatus.CLOSED)
                .label("closed"),
                func.count(Ticket.id).label("total"),
            )
            .select_from(User)
            .outerjoin(Ticket, join_cond)
            .where(User.organization_id == org_id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(Ticket.id).desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "open_tickets": int(o),
                "in_progress_tickets": int(ip),
                "waiting_customer_tickets": int(wc),
                "resolved_tickets": int(r),
                "closed_tickets": int(cl),
                "total_assigned": int(t),
            }
            for agent_id, agent_name, o, ip, wc, r, cl, t in rows
        ]

    # ---------- AI analytics ----------

    async def ai_analytics(
        self,
        org_id: uuid.UUID,
        date_from: date,
        date_to: date,
    ) -> dict:
        start, end = _day_bounds(date_from, date_to)

        status_col = AISuggestion.status
        kind_col = AISuggestion.kind

        overall_stmt = select(
            func.count().label("generated"),
            func.count()
            .filter(status_col == AISuggestionStatus.ACCEPTED)
            .label("accepted"),
            func.count()
            .filter(status_col == AISuggestionStatus.REJECTED)
            .label("rejected"),
            func.count()
            .filter(status_col == AISuggestionStatus.PENDING)
            .label("pending"),
            func.count(func.distinct(AISuggestion.ticket_id))
            .filter(status_col == AISuggestionStatus.ACCEPTED)
            .label("assisted_tickets"),
        ).where(
            AISuggestion.organization_id == org_id,
            AISuggestion.created_at >= start,
            AISuggestion.created_at <= end,
        )
        overall = (await self.db.execute(overall_stmt)).one()

        generated = int(overall.generated)
        accepted = int(overall.accepted)
        rejected = int(overall.rejected)
        pending = int(overall.pending)
        assisted_tickets = int(overall.assisted_tickets)
        acceptance_rate = (
            accepted / (accepted + rejected) * 100
            if (accepted + rejected) > 0
            else 0.0
        )

        by_kind_stmt = (
            select(
                kind_col.label("kind"),
                func.count().label("generated"),
                func.count()
                .filter(status_col == AISuggestionStatus.ACCEPTED)
                .label("accepted"),
                func.count()
                .filter(status_col == AISuggestionStatus.REJECTED)
                .label("rejected"),
            )
            .where(
                AISuggestion.organization_id == org_id,
                AISuggestion.created_at >= start,
                AISuggestion.created_at <= end,
            )
            .group_by(kind_col)
        )
        by_kind = []
        for kind, gen, acc, rej in (await self.db.execute(by_kind_stmt)).all():
            gen, acc, rej = int(gen), int(acc), int(rej)
            rate = acc / (acc + rej) * 100 if (acc + rej) > 0 else 0.0
            by_kind.append(
                {
                    "kind": kind.value if hasattr(kind, "value") else str(kind),
                    "generated": gen,
                    "accepted": acc,
                    "rejected": rej,
                    "acceptance_rate": round(rate, 2),
                }
            )

        confidence_col = AISuggestion.confidence
        bucket_expr = case(
            (confidence_col < 0.2, "0.0-0.2"),
            (confidence_col < 0.4, "0.2-0.4"),
            (confidence_col < 0.6, "0.4-0.6"),
            (confidence_col < 0.8, "0.6-0.8"),
            else_="0.8-1.0",
        )
        conf_stmt = (
            select(bucket_expr.label("bucket"), func.count().label("count"))
            .where(
                AISuggestion.organization_id == org_id,
                AISuggestion.created_at >= start,
                AISuggestion.created_at <= end,
                confidence_col.is_not(None),
            )
            .group_by(bucket_expr)
        )
        conf_raw = {
            str(name): int(c)
            for name, c in (await self.db.execute(conf_stmt)).all()
        }

        buckets_spec = [
            ("0.0-0.2", 0.0, 0.2),
            ("0.2-0.4", 0.2, 0.4),
            ("0.4-0.6", 0.4, 0.6),
            ("0.6-0.8", 0.6, 0.8),
            ("0.8-1.0", 0.8, 1.0),
        ]
        confidence_distribution = [
            {"bucket": name, "min": lo, "max": hi, "count": conf_raw.get(name, 0)}
            for name, lo, hi in buckets_spec
        ]

        return {
            "overall": {
                "suggestions_generated": generated,
                "suggestions_accepted": accepted,
                "suggestions_rejected": rejected,
                "suggestions_pending": pending,
                "acceptance_rate": round(acceptance_rate, 2),
                "assisted_tickets": assisted_tickets,
            },
            "by_kind": by_kind,
            "confidence_distribution": confidence_distribution,
        }