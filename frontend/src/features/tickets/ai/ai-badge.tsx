import { Sparkles } from "lucide-react";

export function AIBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-1.5 py-0.5 text-2xs font-medium text-violet-700 dark:border-violet-900 dark:bg-violet-950/60 dark:text-violet-300">
      <Sparkles className="h-2.5 w-2.5" aria-hidden="true" />
      AI
    </span>
  );
}
