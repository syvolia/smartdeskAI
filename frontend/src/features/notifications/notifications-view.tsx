"use client";

import {
  AlertTriangle,
  Bell,
  Check,
  CheckCheck,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  UserPlus,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
} from "@/features/notifications/mutations";
import { useNotifications } from "@/features/notifications/queries";
import { formatRelativeTime } from "@/lib/utils";
import type { Notification, NotificationType } from "@/types/notification";

const TYPE_ICON: Record<
  NotificationType,
  React.ComponentType<{ className?: string }>
> = {
  TICKET_ASSIGNED: UserPlus,
  TICKET_REASSIGNED: RefreshCw,
  TICKET_COMMENT: MessageSquare,
  TICKET_RESOLVED: CheckCheck,
  TICKET_REOPENED: RotateCcw,
  TICKET_UPDATED: RefreshCw,
  SLA_WARNING: AlertTriangle,
  SLA_BREACHED: AlertTriangle,
  MENTION: Bell,
};

const TYPE_TONE: Partial<Record<NotificationType, string>> = {
  TICKET_RESOLVED: "text-emerald-600 dark:text-emerald-400",
  SLA_WARNING: "text-amber-600 dark:text-amber-400",
  SLA_BREACHED: "text-red-600 dark:text-red-400",
};

function targetHref(n: Notification): string | null {
  if (n.entity_type === "ticket" && n.entity_id)
    return `/tickets/${n.entity_id}`;
  return null;
}

export function NotificationsView() {
  const [mode, setMode] = useState<"all" | "unread">("all");
  const query = useNotifications({
    unreadOnly: mode === "unread",
    pageSize: 50,
  });
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        description="Assignments, comments, SLA alerts, and ticket status changes."
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => markAll.mutate()}
            disabled={
              markAll.isPending || (query.data?.unread_count ?? 0) === 0
            }
          >
            <CheckCheck className="h-4 w-4" aria-hidden="true" />
            Mark all as read
          </Button>
        }
      />

      <Tabs value={mode} onValueChange={(v) => setMode(v as "all" | "unread")}>
        <TabsList aria-label="Notification filter">
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="unread">
            Unread
            {query.data?.unread_count ? (
              <span className="ml-1.5 rounded-full bg-primary px-1.5 text-2xs font-medium text-primary-foreground">
                {query.data.unread_count}
              </span>
            ) : null}
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {query.isLoading && !query.data ? (
        <LoadingState variant="list" rows={5} />
      ) : query.isError ? (
        <ErrorState
          title="Couldn't load notifications"
          onRetry={() => query.refetch()}
        />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState
          icon={Bell}
          title={
            mode === "unread"
              ? "No unread notifications"
              : "You're all caught up"
          }
          description="Notifications about ticket activity will appear here."
        />
      ) : query.data ? (
        <Card className="overflow-hidden">
          <ul role="list" className="divide-y">
            {query.data.items.map((n) => {
              const Icon = TYPE_ICON[n.type] ?? Bell;
              const tone = TYPE_TONE[n.type] ?? "text-muted-foreground";
              const href = targetHref(n);
              const isUnread = n.read_at === null;

              const content = (
                <div className="flex gap-3 p-4">
                  <span
                    aria-hidden="true"
                    className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted ${tone}`}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start gap-2">
                      <p className="truncate text-sm font-medium">{n.title}</p>
                      {isUnread ? (
                        <Badge variant="info" className="shrink-0">
                          New
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {n.body}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatRelativeTime(n.created_at)}
                    </p>
                  </div>
                  {isUnread ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        markRead.mutate(n.id);
                      }}
                      aria-label="Mark as read"
                      disabled={markRead.isPending}
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                  ) : null}
                </div>
              );

              return (
                <li key={n.id}>
                  {href ? (
                    <Link
                      href={href}
                      className="block transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {content}
                    </Link>
                  ) : (
                    content
                  )}
                </li>
              );
            })}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
