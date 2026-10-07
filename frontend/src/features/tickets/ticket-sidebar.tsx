"use client";

import { CheckCircle2, Clock, Loader2, RotateCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  PRIORITY_OPTIONS,
  STATUS_OPTIONS,
} from "@/features/tickets/ticket-options";
import {
  useAssignTicket,
  useChangeTicketPriority,
  useChangeTicketStatus,
} from "@/features/tickets/mutations";
import { useTickets } from "@/features/tickets/queries";
import { formatRelativeTime } from "@/lib/utils";
import type { Ticket, TicketPriority, TicketStatus } from "@/types/ticket";

interface TicketSidebarProps {
  ticket: Ticket;
}

export function TicketSidebar({ ticket }: TicketSidebarProps) {
  // Derive assignee options from a wider ticket list. Replace with a
  // dedicated /agents endpoint when available.
  const ticketList = useTickets({ page: 1, page_size: 100 });

  const assignMutation = useAssignTicket();
  const statusMutation = useChangeTicketStatus();
  const priorityMutation = useChangeTicketPriority();

  const agents = (() => {
    const map = new Map<string, { id: string; full_name: string }>();
    for (const t of ticketList.data?.items ?? []) {
      if (t.assigned_agent) map.set(t.assigned_agent.id, t.assigned_agent);
    }
    if (ticket.assigned_agent) {
      map.set(ticket.assigned_agent.id, ticket.assigned_agent);
    }
    return Array.from(map.values());
  })();

  const isResolved = ticket.status === "RESOLVED" || ticket.status === "CLOSED";

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Manage ticket</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="status">Status</Label>
          <Select
            value={ticket.status}
            onValueChange={(value) =>
              statusMutation.mutate({
                ticketId: ticket.id,
                status: value as TicketStatus,
              })
            }
            disabled={statusMutation.isPending}
          >
            <SelectTrigger id="status" aria-label="Change status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="priority">Priority</Label>
          <Select
            value={ticket.priority}
            onValueChange={(value) =>
              priorityMutation.mutate({
                ticketId: ticket.id,
                priority: value as TicketPriority,
              })
            }
            disabled={priorityMutation.isPending}
          >
            <SelectTrigger id="priority" aria-label="Change priority">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PRIORITY_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="assignee">Assignee</Label>
          <Select
            value={ticket.assigned_agent?.id ?? "__unassigned"}
            onValueChange={(value) =>
              assignMutation.mutate({
                ticketId: ticket.id,
                assigned_agent_id: value === "__unassigned" ? null : value,
              })
            }
            disabled={assignMutation.isPending}
          >
            <SelectTrigger id="assignee" aria-label="Assign ticket">
              <SelectValue placeholder="Unassigned" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__unassigned">Unassigned</SelectItem>
              {agents.length === 0 ? (
                <SelectItem value="__no-agents" disabled>
                  No agents available
                </SelectItem>
              ) : (
                agents.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.full_name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        <Separator />

        <div className="flex flex-wrap gap-2">
          {isResolved ? (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() =>
                statusMutation.mutate({
                  ticketId: ticket.id,
                  status: "OPEN",
                })
              }
              disabled={statusMutation.isPending}
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Reopen
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() =>
                statusMutation.mutate({
                  ticketId: ticket.id,
                  status: "RESOLVED",
                })
              }
              disabled={statusMutation.isPending}
            >
              {statusMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              )}
              Resolve
            </Button>
          )}
        </div>

        <Separator />

        <dl className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-muted-foreground">Team</dt>
            <dd className="min-w-0 truncate text-right font-medium">
              {ticket.team?.name ?? "—"}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-muted-foreground">Category</dt>
            <dd className="min-w-0 truncate text-right font-medium">
              {ticket.category?.name ?? "—"}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-muted-foreground">Source</dt>
            <dd className="text-right font-medium">{ticket.source}</dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-muted-foreground">Created</dt>
            <dd className="text-right font-medium">
              {formatRelativeTime(ticket.created_at)}
            </dd>
          </div>
        </dl>

        {ticket.sla ? (
          <>
            <Separator />
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Clock
                  className="h-4 w-4 text-muted-foreground"
                  aria-hidden="true"
                />
                SLA
                <Badge
                  variant={ticket.sla.sla_breached ? "danger" : "success"}
                  className="ml-auto"
                >
                  {ticket.sla.sla_breached ? "Breached" : "On track"}
                </Badge>
              </div>
              <dl className="space-y-2 text-xs">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">First response</dt>
                  <dd className="text-right font-medium">
                    {ticket.sla.first_response_due_at
                      ? formatRelativeTime(ticket.sla.first_response_due_at)
                      : "—"}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Resolution</dt>
                  <dd className="text-right font-medium">
                    {ticket.sla.resolution_due_at
                      ? formatRelativeTime(ticket.sla.resolution_due_at)
                      : "—"}
                  </dd>
                </div>
              </dl>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
