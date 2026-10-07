"use client";

import { Loader2, Lock, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useAddTicketComment } from "@/features/tickets/mutations";

interface TicketComposerProps {
  ticketId: string;
  /**
   * When set, the composer replaces its body with this text (and switches
   * to "reply" mode) then calls `onExternalDraftConsumed`. Used by the AI
   * Copilot panel's "Insert response" action.
   */
  externalDraft?: string | null;
  onExternalDraftConsumed?: () => void;
}

type Mode = "reply" | "internal";

export function TicketComposer({
  ticketId,
  externalDraft,
  onExternalDraftConsumed,
}: TicketComposerProps) {
  const [mode, setMode] = useState<Mode>("reply");
  const [body, setBody] = useState("");
  const mutation = useAddTicketComment();

  useEffect(() => {
    if (externalDraft == null) return;
    setBody(externalDraft);
    setMode("reply");
    // Scroll the composer into view so the agent sees the result.
    document
      .getElementById("ticket-composer")
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
    onExternalDraftConsumed?.();
  }, [externalDraft, onExternalDraftConsumed]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = body.trim();
    if (!trimmed) return;

    mutation.mutate(
      { ticketId, body: trimmed, is_internal: mode === "internal" },
      {
        onSuccess: () => {
          setBody("");
          setMode("reply");
        },
      },
    );
  };

  return (
    <form
      id="ticket-composer"
      onSubmit={handleSubmit}
      className="scroll-mt-20 space-y-3"
    >
      <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)}>
        <TabsList aria-label="Composer mode">
          <TabsTrigger value="reply">
            <Send className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Reply
          </TabsTrigger>
          <TabsTrigger value="internal">
            <Lock className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Internal note
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="space-y-1.5">
        <Label htmlFor="composer-body" className="sr-only">
          {mode === "internal" ? "Internal note" : "Reply"}
        </Label>
        <Textarea
          id="composer-body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder={
            mode === "internal"
              ? "Write a note only your team will see…"
              : "Write a reply to the customer…"
          }
          rows={4}
          aria-describedby="composer-hint"
          className={
            mode === "internal"
              ? "border-amber-300 bg-amber-50/50 focus-visible:ring-amber-500 dark:border-amber-800 dark:bg-amber-950/20"
              : undefined
          }
        />
        <p id="composer-hint" className="text-xs text-muted-foreground">
          {mode === "internal"
            ? "Internal notes are never shown to customers."
            : "Replies are sent to the customer by email."}
        </p>
      </div>

      <div className="flex items-center justify-end gap-2">
        <Button type="submit" disabled={mutation.isPending || !body.trim()}>
          {mutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Sending…
            </>
          ) : (
            <>
              <Send className="h-4 w-4" aria-hidden="true" />
              {mode === "internal" ? "Add note" : "Send reply"}
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
