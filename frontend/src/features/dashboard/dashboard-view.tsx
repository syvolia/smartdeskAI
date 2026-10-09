"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Inbox,
  Plus,
  Ticket as TicketIcon,
} from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalyticsDashboard } from "@/features/analytics/queries";
import { useAuth } from "@/hooks/use-auth";
import { apiClient, apiV1 } from "@/lib/api-client";
import { formatDuration, formatNumber, formatPercent } from "@/lib/format";
import { formatRelativeTime } from "@/lib/utils";
import type { TicketListResponse } from "@/types/ticket";

// ---------- KPI card ----------

interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: "neutral" | "warning" | "success" | "danger" | "info";
  loading?: boolean;
}

const toneClasses = {
  neutral: "text-muted-foreground",
  warning: "text-amber-600 dark:text-amber-400",
  success: "text-emerald-600 dark:text-emerald-400",
  danger: "text-red-600 dark:text-red-400",
  info: "text-blue-600 dark:text-blue-400",
} as const;

function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
  loading,
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between p-5">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          {loading ? (
            <Skeleton className="mt-2 h-8 w-20" />
          ) : (
            <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">
              {value}
            </p>
          )}
          {loading ? (
            <Skeleton className="mt-2 h-3 w-32" />
          ) : hint ? (
            <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
          ) : null}
        </div>
        <Icon className={`h-5 w-5 shrink-0 ${toneClasses[tone]}`} />
      </CardContent>
    </Card>
  );
}

function complianceTone(pct: number | null): StatCardProps["tone"] {
  if (pct === null) return "neutral";
  if (pct >= 95) return "success";
  if (pct >= 80) return "warning";
  return "danger";
}

// ---------- Staff KPI section ----------

function StaffMetrics() {
  const analytics = useAnalyticsDashboard({});
  const tickets = analytics.data?.tickets;
  const sla = analytics.data?.sla;

  const openCount = tickets
    ? tickets.open + tickets.in_progress + tickets.waiting_customer
    : null;
  const openHint = tickets
    ? `${tickets.in_progress} in progress · ${tickets.waiting_customer} waiting`
    : undefined;

  const compliance = sla?.sla_compliance_percentage ?? null;
  const complianceHint =
    sla && sla.total_with_sla > 0
      ? `${sla.breached} breached of ${sla.total_with_sla}`
      : sla
      ? "No SLAs applied yet"
      : undefined;

  const avgFirstResponse = sla?.first_response_avg_seconds ?? null;
  const avgFirstResponseHint = sla
    ? sla.first_response_samples > 0
      ? `${sla.first_response_samples} sample${
          sla.first_response_samples === 1 ? "" : "s"
        }`
      : "No responses recorded yet"
    : undefined;

  const resolvedCount = tickets?.resolved ?? null;
  const resolvedHint = tickets
    ? `${tickets.closed} closed · ${formatNumber(tickets.total)} total`
    : undefined;

  if (analytics.isError) {
    return (
      <div
        role="status"
        className="rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive"
      >
        Couldn&apos;t load workspace metrics.{" "}
        <button
          type="button"
          onClick={() => analytics.refetch()}
          className="underline underline-offset-2 hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Open tickets"
        value={openCount !== null ? formatNumber(openCount) : "—"}
        hint={openHint}
        icon={Inbox}
        tone="info"
        loading={analytics.isLoading && !analytics.data}
      />
      <StatCard
        label="SLA compliance"
        value={compliance !== null ? formatPercent(compliance) : "—"}
        hint={complianceHint}
        icon={
          compliance !== null && compliance < 90 ? AlertTriangle : CheckCircle2
        }
        tone={complianceTone(compliance)}
        loading={analytics.isLoading && !analytics.data}
      />
      <StatCard
        label="Avg. first response"
        value={formatDuration(avgFirstResponse)}
        hint={avgFirstResponseHint}
        icon={Clock}
        tone="warning"
        loading={analytics.isLoading && !analytics.data}
      />
      <StatCard
        label="Resolved"
        value={resolvedCount !== null ? formatNumber(resolvedCount) : "—"}
        hint={resolvedHint}
        icon={CheckCircle2}
        tone="success"
        loading={analytics.isLoading && !analytics.data}
      />
    </div>
  );
}

// ---------- Customer KPI section ----------

function CustomerMetrics() {
  // Customers only see their own tickets. The list endpoint already
  // scopes by the caller's email, so we just ask for it. No call to
  // /analytics/dashboard — that endpoint is staff-only and would 403.
  const ticketsQuery = useQuery({
    queryKey: ["tickets", "customer-mine"],
    queryFn: () =>
      apiClient.get<TicketListResponse>(apiV1("/tickets"), {
        query: { page: 1, page_size: 100, sort: "updated_at", order: "desc" },
      }),
  });

  if (ticketsQuery.isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Card key={i}>
            <CardContent className="p-5">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="mt-2 h-8 w-12" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (ticketsQuery.isError) {
    return (
      <div
        role="status"
        className="rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive"
      >
        Couldn&apos;t load your tickets.{" "}
        <button
          type="button"
          onClick={() => ticketsQuery.refetch()}
          className="underline underline-offset-2 hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const items = ticketsQuery.data?.items ?? [];
  const open = items.filter((t) => t.status === "OPEN").length;
  const inProgress = items.filter(
    (t) => t.status === "IN_PROGRESS" || t.status === "WAITING_CUSTOMER",
  ).length;
  const resolved = items.filter(
    (t) => t.status === "RESOLVED" || t.status === "CLOSED",
  ).length;

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatCard label="Open" value={String(open)} icon={Inbox} tone="info" />
      <StatCard
        label="In progress"
        value={String(inProgress)}
        icon={Clock}
        tone="warning"
      />
      <StatCard
        label="Resolved"
        value={String(resolved)}
        icon={CheckCircle2}
        tone="success"
      />
    </div>
  );
}

// ---------- View ----------

export function DashboardView() {
  const { user } = useAuth();
  const isStaff = user?.role === "ADMIN" || user?.role === "AGENT";

  const ticketsQuery = useQuery({
    queryKey: ["tickets", "recent"],
    queryFn: () =>
      apiClient.get<TicketListResponse>(apiV1("/tickets"), {
        query: { page: 1, page_size: 5, sort: "updated_at", order: "desc" },
      }),
  });

  const greeting = user?.full_name.split(" ")[0] ?? "there";

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${greeting}`}
        description={
          isStaff
            ? "An overview of your workspace. Track what needs attention and where your team is spending time."
            : "Your support tickets in one place. Open a new request or follow up on an existing one."
        }
        actions={
          <Button asChild>
            <Link href="/tickets/new">
              <Plus className="h-4 w-4" aria-hidden="true" />
              New ticket
            </Link>
          </Button>
        }
      />

      <section aria-labelledby="stats-heading" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 id="stats-heading" className="sr-only">
            Key metrics
          </h2>
          {isStaff ? (
            <p className="text-xs text-muted-foreground">Last 30 days</p>
          ) : null}
        </div>
        {isStaff ? <StaffMetrics /> : <CustomerMetrics />}
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div>
              <CardTitle>
                {isStaff ? "Recent tickets" : "Your recent tickets"}
              </CardTitle>
              <CardDescription>
                {isStaff
                  ? "The five most recently updated tickets in your organization."
                  : "Your five most recently updated tickets."}
              </CardDescription>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href="/tickets">View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {ticketsQuery.isLoading ? (
              <LoadingState variant="table" rows={5} />
            ) : ticketsQuery.isError ? (
              <ErrorState
                title="Couldn't load tickets"
                description="Check your connection and try again."
                onRetry={() => ticketsQuery.refetch()}
              />
            ) : ticketsQuery.data && ticketsQuery.data.items.length > 0 ? (
              <ul role="list" className="divide-y">
                {ticketsQuery.data.items.map((ticket) => (
                  <li key={ticket.id}>
                    <Link
                      href={`/tickets/${ticket.id}`}
                      className="flex items-center justify-between gap-4 rounded-md py-3 transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {ticket.title}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {isStaff ? `${ticket.customer.full_name} · ` : ""}
                          updated {formatRelativeTime(ticket.updated_at)}
                        </p>
                      </div>
                      <Badge
                        variant={
                          ticket.priority === "URGENT"
                            ? "danger"
                            : ticket.priority === "HIGH"
                            ? "warning"
                            : ticket.priority === "LOW"
                            ? "neutral"
                            : "info"
                        }
                      >
                        {ticket.priority}
                      </Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                icon={TicketIcon}
                title={
                  isStaff ? "No tickets yet" : "You haven't opened any tickets"
                }
                description={
                  isStaff
                    ? "When customers reach out, their tickets will show up here."
                    : "When you submit a request, it will appear here."
                }
                action={
                  <Button asChild size="sm">
                    <Link href="/tickets/new">Create a ticket</Link>
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick links</CardTitle>
            <CardDescription>Common destinations</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            <Button asChild variant="outline" className="justify-start">
              <Link href="/tickets">Ticket queue</Link>
            </Button>
            <Button asChild variant="outline" className="justify-start">
              <Link href="/knowledge-base">Knowledge base</Link>
            </Button>
            {isStaff ? (
              <Button asChild variant="outline" className="justify-start">
                <Link href="/analytics">Analytics</Link>
              </Button>
            ) : null}
            <Button asChild variant="outline" className="justify-start">
              <Link href="/settings">Settings</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
