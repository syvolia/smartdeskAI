"use client";

import { Plus, Ticket as TicketIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/pagination";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Button } from "@/components/ui/button";
import {
  PriorityBadge,
  SlaBadge,
  StatusBadge,
} from "@/features/tickets/ticket-badges";
import { TicketFilters } from "@/features/tickets/ticket-filters";
import {
  useTickets,
  type TicketListParams,
} from "@/features/tickets/queries";
import { formatRelativeTime } from "@/lib/utils";
import type { Ticket } from "@/types/ticket";

const DEFAULT_PARAMS: TicketListParams = {
  sort: "updated_at",
  order: "desc",
  page: 1,
  page_size: 20,
};

export function TicketsListView() {
  const router = useRouter();
  const [params, setParams] = useState<TicketListParams>(DEFAULT_PARAMS);

  const query = useTickets(params);

  const updateParams = (next: Partial<TicketListParams>) => {
    setParams((prev) => ({ ...prev, ...next }));
  };

  const columns: DataTableColumn<Ticket>[] = [
    {
      id: "title",
      header: "Title",
      sortable: true,
      cell: (t) => (
        <div className="min-w-0 max-w-[26rem]">
          <p className="truncate font-medium text-foreground">{t.title}</p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {t.id.slice(0, 8)} · {t.source.toLowerCase()}
          </p>
        </div>
      ),
    },
    {
      id: "customer",
      header: "Customer",
      hideBelow: "md",
      cell: (t) => (
        <span className="truncate text-muted-foreground">
          {t.customer.full_name}
        </span>
      ),
    },
    {
      id: "assigned_agent",
      header: "Assignee",
      hideBelow: "lg",
      cell: (t) => (
        <span className="truncate text-muted-foreground">
          {t.assigned_agent?.full_name ?? "Unassigned"}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      sortable: true,
      cell: (t) => <StatusBadge status={t.status} />,
    },
    {
      id: "priority",
      header: "Priority",
      sortable: true,
      cell: (t) => <PriorityBadge priority={t.priority} />,
    },
    {
      id: "sla",
      header: "SLA",
      hideBelow: "lg",
      cell: (t) => (
        <SlaBadge
          breached={Boolean(t.sla?.sla_breached)}
          due={t.sla?.resolution_due_at ?? null}
        />
      ),
    },
    {
      id: "updated_at",
      header: "Updated",
      sortable: true,
      hideBelow: "sm",
      cell: (t) => (
        <span className="whitespace-nowrap text-muted-foreground">
          {formatRelativeTime(t.updated_at)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tickets"
        description="Every customer request routed to your team, in one queue."
        actions={
          <Button asChild>
            <Link href="/tickets/new">
              <Plus className="h-4 w-4" aria-hidden="true" />
              New ticket
            </Link>
          </Button>
        }
      />

      <TicketFilters
        value={params}
        onChange={updateParams}
        tickets={query.data?.items}
        onReset={() => setParams(DEFAULT_PARAMS)}
      />

      {query.isLoading && !query.data ? (
        <LoadingState variant="table" rows={8} />
      ) : query.isError ? (
        <ErrorState
          title="Couldn't load tickets"
          description="The ticket service didn't respond. Try again in a moment."
          onRetry={() => query.refetch()}
        />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState
          icon={TicketIcon}
          title={params.search ? "No matching tickets" : "No tickets yet"}
          description={
            params.search
              ? "Try a different search term or clear your filters."
              : "When customers reach out, their tickets will appear here."
          }
          action={
            !params.search ? (
              <Button asChild size="sm">
                <Link href="/tickets/new">Create the first ticket</Link>
              </Button>
            ) : null
          }
        />
      ) : query.data ? (
        <div className="space-y-4">
          <DataTable
            ariaLabel="Tickets"
            caption="Tickets in your organization. Click a row to open the ticket."
            columns={columns}
            rows={query.data.items}
            rowKey={(t) => t.id}
            rowHref={(t) => `/tickets/${t.id}`}
            onRowClick={(t) => router.push(`/tickets/${t.id}`)}
            sort={params.sort}
            order={params.order}
            onSortChange={(sort, order) =>
              updateParams({ sort, order, page: 1 })
            }
            loading={query.isFetching}
          />
          <DataTablePagination
            page={query.data.page}
            pageSize={query.data.page_size}
            total={query.data.total}
            pages={query.data.pages}
            onPageChange={(page) => updateParams({ page })}
            disabled={query.isFetching}
          />
        </div>
      ) : null}
    </div>
  );
}