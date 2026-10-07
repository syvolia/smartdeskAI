"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Inbox,
  Sparkles,
  Ticket as TicketIcon,
} from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AIConfidenceChart,
  AgentWorkloadChart,
  CategoryDistributionChart,
  PriorityDistributionChart,
  SLAStatsRow,
  TicketStatusChart,
  TicketVolumeChart,
} from "@/features/analytics/charts";
import { DateRangePicker } from "@/features/analytics/date-range-picker";
import { KpiCard } from "@/features/analytics/kpi-card";
import { useAnalyticsDashboard } from "@/features/analytics/queries";
import { formatDuration, formatNumber, formatPercent } from "@/lib/format";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function AnalyticsView() {
  const [dateFrom, setDateFrom] = useState(isoDaysAgo(29));
  const [dateTo, setDateTo] = useState(today());

  const query = useAnalyticsDashboard({
    date_from: dateFrom,
    date_to: dateTo,
    granularity: "day",
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="Volume, SLA performance, agent workload, and AI acceptance."
        actions={
          <DateRangePicker
            dateFrom={dateFrom}
            dateTo={dateTo}
            onChange={(next) => {
              setDateFrom(next.dateFrom);
              setDateTo(next.dateTo);
            }}
          />
        }
      />

      {query.isLoading && !query.data ? (
        <LoadingState variant="page" />
      ) : query.isError ? (
        <ErrorState
          title="Couldn't load analytics"
          description="The analytics service didn't respond. Try again in a moment."
          onRetry={() => query.refetch()}
        />
      ) : query.data ? (
        <AnalyticsBody data={query.data} />
      ) : null}
    </div>
  );
}

function AnalyticsBody({
  data,
}: {
  data: NonNullable<ReturnType<typeof useAnalyticsDashboard>["data"]>;
}) {
  const { tickets, sla, ai } = data;

  return (
    <div className="space-y-6">
      <section aria-labelledby="kpis-heading">
        <h2 id="kpis-heading" className="sr-only">
          Key metrics
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Total tickets"
            value={formatNumber(tickets.total)}
            icon={TicketIcon}
          />
          <KpiCard
            label="Open"
            value={formatNumber(
              tickets.open + tickets.in_progress + tickets.waiting_customer,
            )}
            hint={`${tickets.in_progress} in progress · ${tickets.waiting_customer} waiting`}
            icon={Inbox}
            tone="info"
          />
          <KpiCard
            label="Resolved"
            value={formatNumber(tickets.resolved)}
            hint={`${tickets.closed} closed`}
            icon={CheckCircle2}
            tone="success"
          />
          <KpiCard
            label="SLA compliance"
            value={formatPercent(sla.sla_compliance_percentage)}
            hint={`${sla.breached} breached of ${sla.total_with_sla}`}
            icon={sla.breached > 0 ? AlertTriangle : CheckCircle2}
            tone={sla.breached > 0 ? "warning" : "success"}
          />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Ticket volume</CardTitle>
            <CardDescription>
              Created and resolved tickets over the selected period.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TicketVolumeChart
              created={data.time_series.created}
              resolved={data.time_series.resolved}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>SLA performance</CardTitle>
            <CardDescription>
              Averages are computed on tickets with the relevant timestamp.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SLAStatsRow
              firstResponseAvgSeconds={sla.first_response_avg_seconds}
              resolutionAvgSeconds={sla.resolution_avg_seconds}
              compliance={sla.sla_compliance_percentage}
            />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>By status</CardTitle>
          </CardHeader>
          <CardContent>
            <TicketStatusChart data={tickets.by_status} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>By priority</CardTitle>
          </CardHeader>
          <CardContent>
            <PriorityDistributionChart data={tickets.by_priority} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>By category</CardTitle>
        </CardHeader>
        <CardContent>
          <CategoryDistributionChart data={tickets.by_category} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Agent workload</CardTitle>
          <CardDescription>
            Tickets assigned to each agent, grouped by current status.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.agents.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No agents in this organization yet.
            </p>
          ) : (
            <AgentWorkloadChart rows={data.agents} />
          )}
        </CardContent>
      </Card>

      <section aria-labelledby="ai-heading" className="space-y-4">
        <h2 id="ai-heading" className="text-base font-semibold tracking-tight">
          AI performance
        </h2>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="AI suggestions"
            value={formatNumber(ai.overall.suggestions_generated)}
            icon={Sparkles}
            tone="info"
          />
          <KpiCard
            label="Accepted"
            value={formatNumber(ai.overall.suggestions_accepted)}
            hint={`${ai.overall.suggestions_rejected} rejected`}
            icon={CheckCircle2}
            tone="success"
          />
          <KpiCard
            label="Acceptance rate"
            value={formatPercent(ai.overall.acceptance_rate)}
            hint="Accepted ÷ (accepted + rejected)"
            icon={Sparkles}
            tone="info"
          />
          <KpiCard
            label="AI-assisted tickets"
            value={formatNumber(ai.overall.assisted_tickets)}
            hint="Tickets with at least one accepted suggestion"
            icon={CheckCircle2}
          />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Confidence distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <AIConfidenceChart buckets={ai.confidence_distribution} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Acceptance by kind</CardTitle>
            </CardHeader>
            <CardContent>
              {ai.by_kind.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  No AI suggestions yet.
                </p>
              ) : (
                <ul className="divide-y">
                  {ai.by_kind.map((row) => (
                    <li
                      key={row.kind}
                      className="flex items-center justify-between gap-4 py-3 text-sm"
                    >
                      <span className="font-medium">
                        {row.kind.replace(/_/g, " ").toLowerCase()}
                      </span>
                      <span className="flex gap-4 text-xs text-muted-foreground">
                        <span>{row.generated} generated</span>
                        <span className="text-emerald-600 dark:text-emerald-400">
                          {row.accepted} accepted
                        </span>
                        <span className="text-red-600 dark:text-red-400">
                          {row.rejected} rejected
                        </span>
                        <span className="font-medium text-foreground tabular-nums">
                          {formatPercent(row.acceptance_rate)}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
