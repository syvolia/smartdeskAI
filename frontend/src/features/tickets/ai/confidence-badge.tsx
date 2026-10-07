import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  value: number; // 0..1
  className?: string;
}

export function ConfidenceBadge({ value, className }: ConfidenceBadgeProps) {
  const pct = Math.round(value * 100);
  const tone =
    pct >= 80
      ? "text-emerald-700 dark:text-emerald-400"
      : pct >= 60
      ? "text-amber-700 dark:text-amber-400"
      : "text-muted-foreground";
  return (
    <span
      className={cn("text-2xs font-medium tabular-nums", tone, className)}
      title={`Model confidence: ${pct}%`}
    >
      {pct}% confidence
    </span>
  );
}
