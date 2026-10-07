"use client";

import { cn } from "@/lib/utils";
import { useRealtime } from "@/features/realtime/provider";

export function RealtimeStatus() {
  const { isConnected } = useRealtime();

  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={
        isConnected ? "Live updates connected" : "Live updates offline"
      }
      title={isConnected ? "Live updates connected" : "Live updates offline"}
      className={cn(
        "mr-1 hidden h-2 w-2 shrink-0 rounded-full sm:inline-block",
        isConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
      )}
    />
  );
}
