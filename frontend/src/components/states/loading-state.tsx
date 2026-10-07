import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface LoadingStateProps {
  variant?: "page" | "list" | "table" | "inline";
  rows?: number;
  className?: string;
}

export function LoadingState({
  variant = "page",
  rows = 5,
  className,
}: LoadingStateProps) {
  if (variant === "inline") {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label="Loading"
        className={cn(
          "flex items-center gap-2 text-sm text-muted-foreground",
          className,
        )}
      >
        <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
        Loading…
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div
        role="status"
        aria-label="Loading"
        className={cn("space-y-2", className)}
      >
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (variant === "list") {
    return (
      <div
        role="status"
        aria-label="Loading"
        className={cn("space-y-3", className)}
      >
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-start gap-3 rounded-lg border p-4">
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn("space-y-6", className)}
    >
      <div className="space-y-2">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
