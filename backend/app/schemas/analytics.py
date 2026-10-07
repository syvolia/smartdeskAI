"""Analytics request/response schemas."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------- shared ----------


class DateRange(BaseModel):
    date_from: date | None = None
    date_to: date | None = None


class NameValue(BaseModel):
    name: str
    value: int


class TimeSeriesPoint(BaseModel):
    bucket: datetime
    count: int


# ---------- ticket overview ----------


class TicketOverview(BaseModel):
    total: int
    open: int
    in_progress: int
    waiting_customer: int
    resolved: int
    closed: int
    by_priority: list[NameValue]
    by_status: list[NameValue]
    by_category: list[NameValue]


class TicketTimeSeries(BaseModel):
    created: list[TimeSeriesPoint]
    resolved: list[TimeSeriesPoint]


# ---------- SLA ----------


class SLAMetrics(BaseModel):
    first_response_avg_seconds: float | None
    resolution_avg_seconds: float | None
    first_response_samples: int
    resolution_samples: int
    sla_compliance_percentage: float
    breached: int
    total_with_sla: int


# ---------- agent workload ----------


class AgentWorkloadRow(BaseModel):
    agent_id: UUID | None
    agent_name: str
    open_tickets: int
    in_progress_tickets: int
    waiting_customer_tickets: int
    resolved_tickets: int
    closed_tickets: int
    total_assigned: int


# ---------- AI analytics ----------


class AIOverallMetrics(BaseModel):
    suggestions_generated: int
    suggestions_accepted: int
    suggestions_rejected: int
    suggestions_pending: int
    acceptance_rate: float
    assisted_tickets: int


class AIByKindRow(BaseModel):
    kind: str
    generated: int
    accepted: int
    rejected: int
    acceptance_rate: float


class AIConfidenceBucket(BaseModel):
    bucket: str  # e.g. "0.0-0.2"
    min: float
    max: float
    count: int


class AIAnalytics(BaseModel):
    overall: AIOverallMetrics
    by_kind: list[AIByKindRow]
    confidence_distribution: list[AIConfidenceBucket]


# ---------- combined dashboard ----------


class AnalyticsDashboard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_from: date
    date_to: date
    tickets: TicketOverview
    time_series: TicketTimeSeries
    sla: SLAMetrics
    agents: list[AgentWorkloadRow]
    ai: AIAnalytics


# ---------- query params ----------

Granularity = Literal["day", "week", "month"]