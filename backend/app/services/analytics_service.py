"""Analytics service: shapes raw aggregate rows into API responses."""

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AIAnalytics,
    AIByKindRow,
    AIConfidenceBucket,
    AIOverallMetrics,
    AgentWorkloadRow,
    AnalyticsDashboard,
    NameValue,
    SLAMetrics,
    TicketOverview,
    TicketTimeSeries,
    TimeSeriesPoint,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AnalyticsRepository(db)

    @staticmethod
    def resolve_date_range(
        date_from: date | None, date_to: date | None
    ) -> tuple[date, date]:
        today = date.today()
        if date_from is None and date_to is None:
            return today - timedelta(days=29), today
        if date_from is None:
            return date_to - timedelta(days=29), date_to  # type: ignore[operator]
        if date_to is None:
            return date_from, today
        if date_from > date_to:
            raise ValueError("date_from cannot be after date_to")
        return date_from, date_to

    async def dashboard(
        self,
        org_id: uuid.UUID,
        date_from: date,
        date_to: date,
        *,
        granularity: str = "day",
    ) -> AnalyticsDashboard:
        overview_raw = await self.repo.ticket_overview(org_id, date_from, date_to)
        series_raw = await self.repo.ticket_time_series(
            org_id, date_from, date_to, granularity=granularity
        )
        sla_raw = await self.repo.sla_metrics(org_id, date_from, date_to)
        agents_raw = await self.repo.agent_workload(org_id, date_from, date_to)
        ai_raw = await self.repo.ai_analytics(org_id, date_from, date_to)

        return AnalyticsDashboard(
            date_from=date_from,
            date_to=date_to,
            tickets=TicketOverview(
                total=overview_raw["total"],
                open=overview_raw["open"],
                in_progress=overview_raw["in_progress"],
                waiting_customer=overview_raw["waiting_customer"],
                resolved=overview_raw["resolved"],
                closed=overview_raw["closed"],
                by_priority=[NameValue(**x) for x in overview_raw["by_priority"]],
                by_status=[NameValue(**x) for x in overview_raw["by_status"]],
                by_category=[NameValue(**x) for x in overview_raw["by_category"]],
            ),
            time_series=TicketTimeSeries(
                created=[TimeSeriesPoint(**x) for x in series_raw["created"]],
                resolved=[TimeSeriesPoint(**x) for x in series_raw["resolved"]],
            ),
            sla=SLAMetrics(
                first_response_avg_seconds=sla_raw["first_response_avg_seconds"],
                first_response_samples=sla_raw["first_response_samples"],
                resolution_avg_seconds=sla_raw["resolution_avg_seconds"],
                resolution_samples=sla_raw["resolution_samples"],
                sla_compliance_percentage=sla_raw["sla_compliance_percentage"],
                breached=sla_raw["breached"],
                total_with_sla=sla_raw["total_with_sla"],
            ),
            agents=[AgentWorkloadRow(**x) for x in agents_raw],
            ai=AIAnalytics(
                overall=AIOverallMetrics(**ai_raw["overall"]),
                by_kind=[AIByKindRow(**x) for x in ai_raw["by_kind"]],
                confidence_distribution=[
                    AIConfidenceBucket(**x) for x in ai_raw["confidence_distribution"]
                ],
            ),
        )