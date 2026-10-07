"use client";

import { ErrorState } from "@/components/states/error-state";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ErrorState
      title="This view failed to load"
      description={
        error.message ||
        "An unexpected error occurred. You can retry or navigate away."
      }
      onRetry={reset}
    />
  );
}
