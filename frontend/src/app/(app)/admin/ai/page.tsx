"use client";

import { useEffect, useState } from "react";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdateAIConfig } from "@/features/admin/mutations";
import { useAIConfig } from "@/features/admin/queries";

interface LocalState {
  enabled: boolean;
  auto_summarize: boolean;
  auto_classify: boolean;
  auto_priority: boolean;
  min_confidence: number;
  suggested_response_tone: string;
}

const DEFAULTS: LocalState = {
  enabled: false,
  auto_summarize: true,
  auto_classify: false,
  auto_priority: false,
  min_confidence: 0.6,
  suggested_response_tone: "friendly",
};

export default function AIConfigPage() {
  const query = useAIConfig();
  const update = useUpdateAIConfig();
  const [state, setState] = useState<LocalState>(DEFAULTS);

  useEffect(() => {
    if (query.data) {
      setState({ ...DEFAULTS, ...(query.data as Partial<LocalState>) });
    }
  }, [query.data]);

  if (query.isLoading) return <LoadingState variant="page" />;
  if (query.isError) {
    return (
      <ErrorState
        title="Couldn't load AI configuration"
        onRetry={() => query.refetch()}
      />
    );
  }

  const onToggle = (key: keyof LocalState) =>
    setState((s) => ({ ...s, [key]: !s[key] }));

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    update.mutate(state as unknown as Record<string, unknown>);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI configuration</CardTitle>
        <CardDescription>
          Control which AI capabilities are active for this organization.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-5 max-w-xl">
          <Check
            id="ai-enabled"
            label="Enable AI features"
            description="Master switch. When off, no AI suggestions are generated."
            checked={state.enabled}
            onChange={() => onToggle("enabled")}
          />
          <Check
            id="ai-summarize"
            label="Auto-summarize tickets"
            checked={state.auto_summarize}
            onChange={() => onToggle("auto_summarize")}
          />
          <Check
            id="ai-classify"
            label="Auto-classify categories"
            checked={state.auto_classify}
            onChange={() => onToggle("auto_classify")}
          />
          <Check
            id="ai-priority"
            label="Auto-detect priority"
            checked={state.auto_priority}
            onChange={() => onToggle("auto_priority")}
          />

          <div className="space-y-1.5 max-w-[200px]">
            <Label htmlFor="ai-conf">Minimum confidence</Label>
            <Input
              id="ai-conf"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={state.min_confidence}
              onChange={(e) =>
                setState((s) => ({
                  ...s,
                  min_confidence: parseFloat(e.target.value),
                }))
              }
            />
            <p className="text-xs text-muted-foreground">
              Suggestions below this threshold won&apos;t be shown.
            </p>
          </div>

          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save configuration"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Check({
  id,
  label,
  description,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  description?: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label htmlFor={id} className="flex items-start gap-3 cursor-pointer">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="mt-1 h-4 w-4 rounded border-input text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      />
      <span className="min-w-0">
        <span className="block text-sm font-medium">{label}</span>
        {description ? (
          <span className="block text-xs text-muted-foreground">
            {description}
          </span>
        ) : null}
      </span>
    </label>
  );
}
