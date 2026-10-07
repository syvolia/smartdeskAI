"use client";

import { ArrowLeft, Mail, MessageSquare, Paperclip, User2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PriorityBadge, StatusBadge } from "@/features/tickets/ticket-badges";
import { TicketAICopilot } from "@/features/tickets/ai/ai-copilot-panel";
import { TicketActivity } from "@/features/tickets/ticket-activity";
import { TicketAttachments } from "@/features/tickets/ticket-attachments";
import { TicketComposer } from "@/features/tickets/ticket-composer";
import { TicketSidebar } from "@/features/tickets/ticket-sidebar";
import {
  useTicket,
  useTicketComments,
  useTicketEvents,
} from "@/features/tickets/queries";
import { formatRelativeTime } from "@/lib/utils";

interface TicketDetailViewProps {
  ticketId: string;
}

export function TicketDetailView({ ticketId }: TicketDetailViewProps) {
  const ticketQuery = useTicket(ticketId);
  const commentsQuery = useTicketComments(ticketId, {
    enabled: ticketQuery.isSuccess,
  });
  const eventsQuery = useTicketEvents(ticketId, {
    enabled: ticketQuery.isSuccess,
  });

  const [aiDraft, setAiDraft] = useState<string | null>(null);

  if (ticketQuery.isLoading) {
    return <LoadingState variant="page" />;
  }

  if (ticketQuery.isError || !ticketQuery.data) {
    return (
      <ErrorState
        title="Couldn't load this ticket"
        description="It may have been deleted, or the service is unavailable."
        onRetry={() => ticketQuery.refetch()}
        action={
          <Button asChild variant="outline">
            <Link href="/tickets">Back to tickets</Link>
          </Button>
        }
      />
    );
  }

  const ticket = ticketQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2">
          <Link href="/tickets">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to tickets
          </Link>
        </Button>
        <PageHeader
          title={ticket.title}
          description={`#${ticket.id.slice(0, 8)} · opened by ${
            ticket.customer.full_name
          } · created ${formatRelativeTime(ticket.created_at)}`}
          actions={
            <div className="flex gap-2">
              <StatusBadge status={ticket.status} />
              <PriorityBadge priority={ticket.priority} />
            </div>
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Description</CardTitle>
              <CardDescription>
                Original request from {ticket.customer.full_name}.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {ticket.description}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Conversation</CardTitle>
              <CardDescription>
                Replies are visible to the customer. Internal notes are not.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {commentsQuery.isLoading ? (
                <LoadingState variant="list" rows={3} />
              ) : commentsQuery.isError ? (
                <ErrorState
                  title="Couldn't load the conversation"
                  onRetry={() => commentsQuery.refetch()}
                />
              ) : commentsQuery.data && commentsQuery.data.items.length > 0 ? (
                <ul role="list" className="space-y-5">
                  {commentsQuery.data.items.map((comment) => (
                    <li key={comment.id} className="flex gap-3">
                      <div
                        aria-hidden="true"
                        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground"
                      >
                        {comment.author?.full_name.charAt(0) ?? "?"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium">
                            {comment.author?.full_name ?? "You"}
                          </span>
                          {comment.is_internal ? (
                            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-2xs font-medium uppercase tracking-wide text-amber-900 dark:bg-amber-950 dark:text-amber-300">
                              Internal note
                            </span>
                          ) : null}
                          {comment.id.startsWith("optimistic-") ? (
                            <span className="text-2xs text-muted-foreground">
                              sending…
                            </span>
                          ) : null}
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(comment.created_at)}
                          </span>
                        </div>
                        <div
                          className={
                            comment.is_internal
                              ? "mt-1.5 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/30"
                              : "mt-1.5 whitespace-pre-wrap text-sm"
                          }
                        >
                          {comment.body}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No messages yet. Start the conversation below.
                </p>
              )}

              <Separator />

              <TicketComposer
                ticketId={ticket.id}
                externalDraft={aiDraft}
                onExternalDraftConsumed={() => setAiDraft(null)}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="activity">
                <TabsList>
                  <TabsTrigger value="activity">
                    <MessageSquare
                      className="mr-1.5 h-3.5 w-3.5"
                      aria-hidden="true"
                    />
                    Activity
                  </TabsTrigger>
                  <TabsTrigger value="attachments">
                    <Paperclip
                      className="mr-1.5 h-3.5 w-3.5"
                      aria-hidden="true"
                    />
                    Attachments
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="activity">
                  <TicketActivity
                    events={eventsQuery.data?.items}
                    loading={eventsQuery.isLoading}
                    error={eventsQuery.isError}
                    onRetry={() => eventsQuery.refetch()}
                  />
                </TabsContent>
                <TabsContent value="attachments">
                  <TicketAttachments ticketId={ticket.id} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <TicketAICopilot
            ticket={ticket}
            onInsertResponse={(text) => setAiDraft(text)}
          />

          <TicketSidebar ticket={ticket} />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Customer</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center gap-2">
                <User2
                  className="h-4 w-4 text-muted-foreground"
                  aria-hidden="true"
                />
                <span className="truncate font-medium">
                  {ticket.customer.full_name}
                </span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Mail className="h-4 w-4" aria-hidden="true" />
                <span className="truncate">{ticket.customer.email}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
