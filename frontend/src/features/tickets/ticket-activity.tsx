"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  Tag,
  UserPlus,
  XCircle,
} from "lucide-react";
import type { ComponentType } from "react";

import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { formatRelativeTime } from "@/lib/utils";
import type { TicketEvent, TicketEventType } from "@/types/ticket";

interface TicketActivityProps {
  events?: TicketEvent[];
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}

const ICONS: Record<TicketEventType, ComponentType<{ className?: string }>> = {
  TICKET_CREATED: MessageSquare,
  TICKET_UPDATED: RefreshCw,
  TICKET_ASSIGNED: UserPlus,
  TICKET_REASSIGNED: UserPlus,
  STATUS_CHANGED: RefreshCw,
  PRIORITY_CHANGED: Tag,
  COMMENT_ADDED: MessageSquare,
  TICKET_RESOLVED: CheckCircle2,
  TICKET_REOPENED: RotateCcw,
  TICKET_CLOSED: XCircle,
  SLA_POLICY_APPLIED: Clock,
  SLA_BREACHED: AlertTriangle,
};

const TONES: Partial<Record<TicketEventType, string>> = {
  TICKET_RESOLVED: "text-emerald-600 dark:text-emerald-400",
  TICKET_CLOSED: "text-muted-foreground",
  TICKET_REOPENED: "text-amber-600 dark:text-amber-400",
  SLA_BREACHED: "text-red-600 dark:text-red-400",
};

function humanize(eventType: TicketEventType): string {
  return eventType.replace(/_/g, " ").toLowerCase();
}

function formatTransition(event: TicketEvent): string | null {
  if (!event.from_value && !event.to_value) return null;
  if (event.from_value && event.to_value) {
    return `${event.from_value} → ${event.to_value}`;
  }
  return event.to_value ?? event.from_value ?? null;
}

export function TicketActivity({
  events,
  loading,
  error,
  onRetry,
}: TicketActivityProps) {
  if (loading) return <LoadingState variant="list" rows={4} />;
  if (error) {
    return <ErrorState title="Couldn't load activity" onRetry={onRetry} />;
  }
  if (!events || events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No activity recorded yet.</p>
    );
  }

  return (
    <ol className="space-y-4">
      {events.map((event) => {
        const Icon = ICONS[event.event_type] ?? RefreshCw;
        const tone = TONES[event.event_type] ?? "text-muted-foreground";
        const transition = formatTransition(event);

        return (
          <li key={event.id} className="flex gap-3">
            <span
              aria-hidden="true"
              className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted ${tone}`}
            >
              <Icon className="h-3.5 w-3.5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm">
                <span className="font-medium">
                  {event.actor?.full_name ?? "System"}
                </span>{" "}
                <span className="text-muted-foreground">
                  {humanize(event.event_type)}
                </span>
                {transition ? (
                  <span className="ml-1 font-medium">{transition}</span>
                ) : null}
              </p>
              {event.note ? (
                <p className="mt-0.5 whitespace-pre-wrap text-xs text-muted-foreground">
                  {event.note}
                </p>
              ) : null}
              <p className="mt-0.5 text-xs text-muted-foreground">
                {formatRelativeTime(event.created_at)}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
