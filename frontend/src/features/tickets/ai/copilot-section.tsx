"use client";

import { Loader2, RefreshCw, Sparkles, X } from "lucide-react";
import type { ComponentType, ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AIBadge } from "@/features/tickets/ai/ai-badge";
import { cn } from "@/lib/utils";
import type { AISuggestion } from "@/types/ai";

interface CopilotSectionProps {
  icon: ComponentType<{ className?: string }>;
  title: string;
  suggestion: AISuggestion | null;
  isGenerating: boolean;
  error: Error | null;
  onGenerate: () => void;
  onRegenerate?: () => void;
  onDismiss?: () => void;
  /** Rendered when a suggestion exists and is not generating. */
  children: ReactNode;
  /** Footer actions inside the body (Apply, Insert, Edit, ...). */
  footer?: ReactNode;
  /** Hide the AI badge when content is informational (no per-item apply). */
  hideBadge?: boolean;
}

export function CopilotSection({
  icon: Icon,
  title,
  suggestion,
  isGenerating,
  error,
  onGenerate,
  onRegenerate,
  onDismiss,
  children,
  footer,
  hideBadge,
}: CopilotSectionProps) {
  const hasSuggestion = Boolean(suggestion) && !isGenerating;

  return (
    <section>
      <header className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Icon
            className="h-3.5 w-3.5 shrink-0 text-violet-600 dark:text-violet-400"
            aria-hidden="true"
          />
          <h4 className="truncate text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {title}
          </h4>
          {hasSuggestion && !hideBadge ? <AIBadge /> : null}
        </div>

        <div className="flex items-center gap-1">
          {hasSuggestion ? (
            <>
              {onRegenerate ? (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={onRegenerate}
                  disabled={isGenerating}
                  aria-label={`Regenerate ${title.toLowerCase()}`}
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              ) : null}
              {onDismiss ? (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={onDismiss}
                  aria-label={`Dismiss ${title.toLowerCase()}`}
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              ) : null}
            </>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={onGenerate}
              disabled={isGenerating}
              className="h-7 px-2 text-xs"
            >
              {isGenerating ? (
                <>
                  <Loader2
                    className="h-3.5 w-3.5 animate-spin"
                    aria-hidden="true"
                  />
                  Generating…
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                  Generate
                </>
              )}
            </Button>
          )}
        </div>
      </header>

      <div className="mt-2">
        {isGenerating && !suggestion ? (
          <div className="space-y-2">
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ) : error && !suggestion ? (
          <div
            role="status"
            className="rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive"
          >
            <p className="font-medium">AI couldn&apos;t generate this</p>
            <p className="mt-0.5 opacity-90">{error.message}</p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-1 h-6 px-2 text-xs"
              onClick={onGenerate}
            >
              Try again
            </Button>
          </div>
        ) : hasSuggestion ? (
          <div className={cn("space-y-3")}>
            <div>{children}</div>
            {footer ? (
              <div className="flex flex-wrap gap-2">{footer}</div>
            ) : null}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            No suggestion yet. Generate one to see it here.
          </p>
        )}
      </div>
    </section>
  );
}
