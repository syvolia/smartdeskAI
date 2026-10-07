"use client";

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";

import { apiClient, apiV1 } from "@/lib/api-client";
import type {
  AISuggestion,
  AISuggestionKind,
  AISuggestionListResponse,
} from "@/types/ai";

export const aiKeys = {
  all: ["ai"] as const,
  suggestionsForTicket: (ticketId: string) =>
    [...aiKeys.all, "suggestions", ticketId] as const,
};

export function useAISuggestions(
  ticketId: string,
  options?: Omit<
    UseQueryOptions<AISuggestionListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<AISuggestionListResponse, Error>({
    queryKey: aiKeys.suggestionsForTicket(ticketId),
    queryFn: () =>
      apiClient.get<AISuggestionListResponse>(
        apiV1(`/ai/tickets/${ticketId}/suggestions`)
      ),
    enabled: Boolean(ticketId),
    // A failed AI fetch shouldn't retry aggressively or block the ticket.
    retry: 0,
    staleTime: 15_000,
    ...options,
  });
}

/** Newest PENDING suggestion of a given kind, or null. */
export function pickPending(
  items: AISuggestion[] | undefined,
  kind: AISuggestionKind
): AISuggestion | null {
  if (!items) return null;
  for (const s of items) {
    if (s.kind === kind && s.status === "PENDING") return s;
  }
  return null;
}

/** Newest suggestion of a given kind regardless of status, or null. */
export function pickLatest(
  items: AISuggestion[] | undefined,
  kind: AISuggestionKind
): AISuggestion | null {
  if (!items) return null;
  for (const s of items) {
    if (s.kind === kind) return s;
  }
  return null;
}