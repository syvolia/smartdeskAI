"use client";

import { Filter, Search, X } from "lucide-react";
import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  PRIORITY_OPTIONS,
  SORT_OPTIONS,
  STATUS_OPTIONS,
} from "@/features/tickets/ticket-options";
import type { TicketListParams } from "@/features/tickets/queries";
import type { Ticket, TicketPriority, TicketStatus } from "@/types/ticket";

interface TicketFiltersProps {
  value: TicketListParams;
  onChange: (next: Partial<TicketListParams>) => void;
  /** Current page of tickets — used to derive assignee/team/customer options. */
  tickets?: Ticket[];
  onReset: () => void;
}

interface Option {
  value: string;
  label: string;
}

function uniqBy<T>(items: T[], key: (item: T) => string): T[] {
  const seen = new Set<string>();
  const out: T[] = [];
  for (const item of items) {
    const k = key(item);
    if (!seen.has(k)) {
      seen.add(k);
      out.push(item);
    }
  }
  return out;
}

export function TicketFilters({
  value,
  onChange,
  tickets = [],
  onReset,
}: TicketFiltersProps) {
  const agentOptions: Option[] = useMemo(() => {
    const agents = tickets
      .map((t) => t.assigned_agent)
      .filter((a): a is NonNullable<typeof a> => Boolean(a));
    return uniqBy(agents, (a) => a.id).map((a) => ({
      value: a.id,
      label: a.full_name,
    }));
  }, [tickets]);

  const teamOptions: Option[] = useMemo(() => {
    const teams = tickets
      .map((t) => t.team)
      .filter((t): t is NonNullable<typeof t> => Boolean(t));
    return uniqBy(teams, (t) => t.id).map((t) => ({
      value: t.id,
      label: t.name,
    }));
  }, [tickets]);

  const customerOptions: Option[] = useMemo(() => {
    const customers = tickets.map((t) => t.customer);
    return uniqBy(customers, (c) => c.id).map((c) => ({
      value: c.id,
      label: c.full_name,
    }));
  }, [tickets]);

  const hasActiveFilter =
    Boolean(value.search) ||
    (value.status?.length ?? 0) > 0 ||
    (value.priority?.length ?? 0) > 0 ||
    Boolean(value.assigned_agent_id) ||
    Boolean(value.team_id) ||
    Boolean(value.customer_id);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            placeholder="Search title or description…"
            value={value.search ?? ""}
            onChange={(e) => onChange({ search: e.target.value, page: 1 })}
            className="pl-8"
            aria-label="Search tickets"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={value.status?.[0] ?? "ALL"}
            onValueChange={(v) =>
              onChange({
                status: v === "ALL" ? undefined : [v as TicketStatus],
                page: 1,
              })
            }
          >
            <SelectTrigger
              className="w-full md:w-[160px]"
              aria-label="Filter by status"
            >
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All statuses</SelectItem>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={value.priority?.[0] ?? "ALL"}
            onValueChange={(v) =>
              onChange({
                priority: v === "ALL" ? undefined : [v as TicketPriority],
                page: 1,
              })
            }
          >
            <SelectTrigger
              className="w-full md:w-[150px]"
              aria-label="Filter by priority"
            >
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All priorities</SelectItem>
              {PRIORITY_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={value.assigned_agent_id ?? "ALL"}
            onValueChange={(v) =>
              onChange({
                assigned_agent_id: v === "ALL" ? undefined : v,
                page: 1,
              })
            }
          >
            <SelectTrigger
              className="w-full md:w-[170px]"
              aria-label="Filter by assigned agent"
            >
              <SelectValue placeholder="Assignee" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All assignees</SelectItem>
              {agentOptions.length === 0 ? (
                <SelectItem value="__empty" disabled>
                  No agents in this view
                </SelectItem>
              ) : (
                agentOptions.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>

          <Select
            value={value.team_id ?? "ALL"}
            onValueChange={(v) =>
              onChange({ team_id: v === "ALL" ? undefined : v, page: 1 })
            }
          >
            <SelectTrigger
              className="w-full md:w-[150px]"
              aria-label="Filter by team"
            >
              <SelectValue placeholder="Team" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All teams</SelectItem>
              {teamOptions.length === 0 ? (
                <SelectItem value="__empty" disabled>
                  No teams in this view
                </SelectItem>
              ) : (
                teamOptions.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>

          <Select
            value={value.customer_id ?? "ALL"}
            onValueChange={(v) =>
              onChange({ customer_id: v === "ALL" ? undefined : v, page: 1 })
            }
          >
            <SelectTrigger
              className="w-full md:w-[170px]"
              aria-label="Filter by customer"
            >
              <SelectValue placeholder="Customer" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All customers</SelectItem>
              {customerOptions.length === 0 ? (
                <SelectItem value="__empty" disabled>
                  No customers in this view
                </SelectItem>
              ) : (
                customerOptions.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>

          <Select
            value={value.sort ?? "updated_at"}
            onValueChange={(v) => onChange({ sort: v })}
          >
            <SelectTrigger className="w-full md:w-[160px]" aria-label="Sort by">
              <SelectValue placeholder="Sort" />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              onChange({
                order: value.order === "asc" ? "desc" : "asc",
              })
            }
            aria-label={`Sort direction: ${value.order ?? "desc"}`}
          >
            <Filter className="h-4 w-4" aria-hidden="true" />
            {value.order === "asc" ? "Ascending" : "Descending"}
          </Button>

          {hasActiveFilter ? (
            <Button variant="ghost" size="sm" onClick={onReset}>
              <X className="h-4 w-4" aria-hidden="true" />
              Clear
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
