"use client";

import { BookOpen, CornerDownLeft, Pencil, Save, X } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ConfidenceBadge } from "@/features/tickets/ai/confidence-badge";
import { SentimentBadge } from "@/features/tickets/ai/sentiment-badge";
import { PriorityBadge } from "@/features/tickets/ticket-badges";
import {
  asClassificationPayload,
  asNextActionPayload,
  asPriorityPayload,
  asSuggestedResponsePayload,
  asSummaryPayload,
  type NextAction,
} from "@/types/ai";

// ---------- Summary ----------

export function SummaryBody({
  payload,
}: {
  payload: Record<string, unknown>;
}) {
  const { summary, key_points, customer_sentiment } = asSummaryPayload(payload);
  return (
    <div className="space-y-2">
      <p className="text-sm leading-relaxed text-foreground">{summary}</p>
      {key_points.length > 0 ? (
        <ul className="list-disc space-y-1 pl-4 text-xs text-muted-foreground">
          {key_points.map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
      ) : null}
      <div className="pt-1">
        <SentimentBadge value={customer_sentiment} />
      </div>
    </div>
  );
}

// ---------- Classification ----------

export function ClassificationBody({
  payload,
  currentCategoryName,
}: {
  payload: Record<string, unknown>;
  currentCategoryName: string | null;
}) {
  const { category_name, reasoning_summary, confidence, category_id } =
    asClassificationPayload(payload);
  const sameAsCurrent = currentCategoryName === category_name;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Badge variant="info">{category_name}</Badge>
        <ConfidenceBadge value={confidence} />
      </div>
      <p className="text-xs text-muted-foreground">{reasoning_summary}</p>
      {sameAsCurrent ? (
        <p className="text-2xs text-muted-foreground">
          Already matches the ticket&apos;s current category.
        </p>
      ) : null}
      {!sameAsCurrent && category_id === null ? (
        <p className="text-2xs text-muted-foreground">
          This category doesn&apos;t exist in your organization yet, so it
          can&apos;t be applied automatically.
        </p>
      ) : null}
    </div>
  );
}

// ---------- Priority ----------

export function PriorityBody({
  payload,
}: {
  payload: Record<string, unknown>;
}) {
  const { suggested_priority, reasoning_summary, confidence } =
    asPriorityPayload(payload);
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <PriorityBadge priority={suggested_priority} />
        <ConfidenceBadge value={confidence} />
      </div>
      <p className="text-xs text-muted-foreground">{reasoning_summary}</p>
    </div>
  );
}

// ---------- Next action ----------

const NEXT_ACTION_LABELS: Record<NextAction, string> = {
  request_information: "Request information",
  provide_solution: "Provide solution",
  escalate: "Escalate",
  assign_specialist: "Assign specialist",
  resolve: "Resolve",
};

export function NextActionBody({
  payload,
}: {
  payload: Record<string, unknown>;
}) {
  const { action, reasoning_summary, confidence } = asNextActionPayload(payload);
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Badge variant="info">{NEXT_ACTION_LABELS[action]}</Badge>
        <ConfidenceBadge value={confidence} />
      </div>
      <p className="text-xs text-muted-foreground">{reasoning_summary}</p>
    </div>
  );
}

// ---------- Suggested response ----------

export function SuggestedResponseBody({
  payload,
  onInsert,
}: {
  payload: Record<string, unknown>;
  onInsert: (text: string) => void;
}) {
  const { draft, tone, cited_articles } = asSuggestedResponsePayload(payload);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(draft);

  const startEdit = () => {
    setValue(draft);
    setEditing(true);
  };
  const cancelEdit = () => {
    setValue(draft);
    setEditing(false);
  };
  const saveEdit = () => {
    setEditing(false);
  };

  return (
    <div className="space-y-3">
      {editing ? (
        <div className="space-y-2">
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            rows={6}
            aria-label="Edit suggested response"
            className="text-sm"
          />
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={saveEdit}>
              <Save className="h-3.5 w-3.5" aria-hidden="true" />
              Save
            </Button>
            <Button size="sm" variant="ghost" onClick={cancelEdit}>
              <X className="h-3.5 w-3.5" aria-hidden="true" />
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="rounded-md border border-violet-200/70 bg-violet-50/50 p-3 text-sm leading-relaxed dark:border-violet-900/50 dark:bg-violet-950/20">
            {value}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="neutral">Tone: {tone}</Badge>
          </div>

          {cited_articles && cited_articles.length > 0 ? (
            <div className="rounded-md border bg-card p-2.5">
              <p className="mb-1.5 text-2xs font-semibold uppercase tracking-wide text-muted-foreground">
                Sources
              </p>
              <ul className="space-y-1.5">
                {cited_articles.map((article) => (
                  <li
                    key={article.id}
                    className="flex items-start gap-2 text-xs"
                  >
                    <BookOpen
                      className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <p className="truncate font-medium">{article.title}</p>
                      <p className="line-clamp-2 text-muted-foreground">
                        {article.excerpt}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              onClick={() => onInsert(value)}
              aria-label="Insert suggested response into composer"
            >
              <CornerDownLeft className="h-3.5 w-3.5" aria-hidden="true" />
              Insert response
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={startEdit}
              aria-label="Edit suggested response"
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              Edit
            </Button>
          </div>
        </>
      )}
    </div>
  );
}