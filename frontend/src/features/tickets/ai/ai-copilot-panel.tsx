"use client";

import {
  BookOpen,
  Check,
  CircleDashed,
  ListChecks,
  Loader2,
  Sparkles,
  Tag,
  Zap,
} from "lucide-react";
import { useCallback } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  ClassificationBody,
  NextActionBody,
  PriorityBody,
  SuggestedResponseBody,
  SummaryBody,
} from "@/features/tickets/ai/bodies";
import { CopilotSection } from "@/features/tickets/ai/copilot-section";
import {
  useAcceptSuggestion,
  useGenerateAll,
  useGenerateClassification,
  useGenerateNextAction,
  useGeneratePriority,
  useGenerateResponse,
  useGenerateSummary,
  useRejectSuggestion,
} from "@/features/tickets/ai/mutations";
import { pickPending, useAISuggestions } from "@/features/tickets/ai/queries";
import {
  useChangeTicketPriority,
  useUpdateTicket,
} from "@/features/tickets/mutations";
import { asPriorityPayload } from "@/types/ai";
import type { AISuggestion } from "@/types/ai";
import type { Ticket } from "@/types/ticket";

interface TicketAICopilotProps {
  ticket: Ticket;
  onInsertResponse: (text: string) => void;
}

export function TicketAICopilot({
  ticket,
  onInsertResponse,
}: TicketAICopilotProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const suggestionsQuery = useAISuggestions(ticket.id);
  const suggestions = suggestionsQuery.data?.items;

  const summary = pickPending(suggestions, "SUMMARY");
  const classification = pickPending(suggestions, "CLASSIFICATION");
  const priority = pickPending(suggestions, "PRIORITY");
  const nextAction = pickPending(suggestions, "NEXT_ACTION");
  const response = pickPending(suggestions, "SUGGESTED_RESPONSE");

  const generateSummary = useGenerateSummary(ticket.id);
  const generateClassification = useGenerateClassification(ticket.id);
  const generatePriority = useGeneratePriority(ticket.id);
  const generateNextAction = useGenerateNextAction(ticket.id);
  const generateResponse = useGenerateResponse(ticket.id);

  const accept = useAcceptSuggestion(ticket.id);
  const reject = useRejectSuggestion(ticket.id);

  const changePriority = useChangeTicketPriority();
  const updateTicket = useUpdateTicket();

  const generateAll = useGenerateAll(ticket.id);

  const dismiss = useCallback(
    (suggestion: AISuggestion, label: string) => {
      reject.mutate(
        { suggestionId: suggestion.id },
        {
          onSuccess: () => toast({ title: `Dismissed ${label} suggestion` }),
        },
      );
    },
    [reject, toast],
  );

  const applyPriority = useCallback(
    async (suggestion: AISuggestion) => {
      const payload = asPriorityPayload(suggestion.payload);
      try {
        await changePriority.mutateAsync({
          ticketId: ticket.id,
          priority: payload.suggested_priority,
        });
        await accept.mutateAsync(suggestion.id);
        toast({
          title: "Priority applied",
          description: `Ticket priority set to ${payload.suggested_priority}.`,
          variant: "success",
        });
      } catch {
        // toasts already fired by underlying mutations
      }
    },
    [accept, changePriority, ticket.id, toast],
  );

  const applyClassification = useCallback(
    async (suggestion: AISuggestion) => {
      const payload = suggestion.payload as { category_id: string | null };
      if (!payload.category_id) {
        toast({
          title: "Can't apply this suggestion",
          description:
            "The suggested category doesn't exist in your organization yet.",
          variant: "destructive",
        });
        return;
      }
      try {
        await updateTicket.mutateAsync({
          ticketId: ticket.id,
          category_id: payload.category_id,
        });
        await accept.mutateAsync(suggestion.id);
        toast({
          title: "Category applied",
          variant: "success",
        });
      } catch {
        // toasts already fired
      }
    },
    [accept, ticket.id, toast, updateTicket],
  );

  const acknowledge = useCallback(
    (suggestion: AISuggestion, label: string) => {
      accept.mutate(suggestion.id, {
        onSuccess: () => toast({ title: `${label} acknowledged` }),
      });
    },
    [accept, toast],
  );

  // Customers don't have copilot access. Hide the entire panel.
  if (user?.role === "CUSTOMER") return null;

  return (
    <Card className="border-violet-200/70 dark:border-violet-900/60">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div className="flex min-w-0 items-center gap-2">
          <Sparkles
            className="h-4 w-4 shrink-0 text-violet-600 dark:text-violet-400"
            aria-hidden="true"
          />
          <CardTitle className="text-sm">AI Copilot</CardTitle>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={generateAll.run}
          disabled={generateAll.isPending}
        >
          {generateAll.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          Generate all
        </Button>
      </CardHeader>

      <CardContent className="space-y-5">
        {suggestionsQuery.isError ? (
          <div
            role="status"
            className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground"
          >
            <p className="font-medium text-foreground">AI is unavailable</p>
            <p className="mt-0.5">
              Suggestions can&apos;t be loaded right now. The ticket works
              normally — try again when the service recovers.
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-1 h-7 px-2 text-xs"
              onClick={() => suggestionsQuery.refetch()}
            >
              Retry
            </Button>
          </div>
        ) : null}

        <CopilotSection
          icon={ListChecks}
          title="Summary"
          suggestion={summary}
          isGenerating={generateSummary.isPending}
          error={generateSummary.error}
          onGenerate={() => generateSummary.mutate()}
          onRegenerate={() => generateSummary.mutate()}
          onDismiss={() => summary && dismiss(summary, "summary")}
        >
          {summary ? <SummaryBody payload={summary.payload} /> : null}
        </CopilotSection>

        <Separator />

        <CopilotSection
          icon={Tag}
          title="Suggested category"
          suggestion={classification}
          isGenerating={generateClassification.isPending}
          error={generateClassification.error}
          onGenerate={() => generateClassification.mutate()}
          onRegenerate={() => generateClassification.mutate()}
          onDismiss={
            classification
              ? () => dismiss(classification, "category")
              : undefined
          }
          footer={
            classification ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => applyClassification(classification)}
                  disabled={
                    (classification.payload as { category_id?: string | null })
                      .category_id === null
                  }
                >
                  <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  Apply
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => dismiss(classification, "category")}
                >
                  Dismiss
                </Button>
              </>
            ) : undefined
          }
        >
          {classification ? (
            <ClassificationBody
              payload={classification.payload}
              currentCategoryName={ticket.category?.name ?? null}
            />
          ) : null}
        </CopilotSection>

        <Separator />

        <CopilotSection
          icon={Zap}
          title="Suggested priority"
          suggestion={priority}
          isGenerating={generatePriority.isPending}
          error={generatePriority.error}
          onGenerate={() => generatePriority.mutate()}
          onRegenerate={() => generatePriority.mutate()}
          onDismiss={priority ? () => dismiss(priority, "priority") : undefined}
          footer={
            priority ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => applyPriority(priority)}
                  disabled={changePriority.isPending || accept.isPending}
                >
                  <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  Apply
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => dismiss(priority, "priority")}
                >
                  Dismiss
                </Button>
              </>
            ) : undefined
          }
        >
          {priority ? <PriorityBody payload={priority.payload} /> : null}
        </CopilotSection>

        <Separator />

        <CopilotSection
          icon={CircleDashed}
          title="Suggested next action"
          suggestion={nextAction}
          isGenerating={generateNextAction.isPending}
          error={generateNextAction.error}
          onGenerate={() => generateNextAction.mutate()}
          onRegenerate={() => generateNextAction.mutate()}
          onDismiss={
            nextAction ? () => dismiss(nextAction, "next action") : undefined
          }
          footer={
            nextAction ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => acknowledge(nextAction, "Next action")}
                  disabled={accept.isPending}
                >
                  <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  Acknowledge
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => dismiss(nextAction, "next action")}
                >
                  Dismiss
                </Button>
              </>
            ) : undefined
          }
        >
          {nextAction ? <NextActionBody payload={nextAction.payload} /> : null}
        </CopilotSection>

        <Separator />

        <CopilotSection
          icon={BookOpen}
          title="Suggested response"
          suggestion={response}
          isGenerating={generateResponse.isPending}
          error={generateResponse.error}
          onGenerate={() => generateResponse.mutate()}
          onRegenerate={() => generateResponse.mutate()}
          onDismiss={response ? () => dismiss(response, "response") : undefined}
        >
          {response ? (
            <SuggestedResponseBody
              payload={response.payload}
              onInsert={(text) => {
                onInsertResponse(text);
                accept.mutate(response.id);
                toast({
                  title: "Draft inserted into composer",
                  description: "Review it before sending.",
                  variant: "success",
                });
              }}
            />
          ) : null}
        </CopilotSection>
      </CardContent>
    </Card>
  );
}
