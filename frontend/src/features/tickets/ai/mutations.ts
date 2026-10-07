"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/hooks/use-toast";
import { apiClient, apiV1, ApiError } from "@/lib/api-client";
import { aiKeys } from "@/features/tickets/ai/queries";
import type { AIAcceptResponse, AISuggestion } from "@/types/ai";

// ---------- generation ----------

function useGenerate(
  ticketId: string,
  path: string,
  label: string
) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<AISuggestion, ApiError, void>({
    mutationFn: () =>
      apiClient.post<AISuggestion>(apiV1(`/ai/tickets/${ticketId}${path}`)),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: aiKeys.suggestionsForTicket(ticketId),
      });
    },
    onError: (error) => {
      toast({
        title: `Couldn't generate ${label}`,
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export const useGenerateSummary = (ticketId: string) =>
  useGenerate(ticketId, "/summarize", "summary");

export const useGenerateClassification = (ticketId: string) =>
  useGenerate(ticketId, "/classify", "category suggestion");

export const useGeneratePriority = (ticketId: string) =>
  useGenerate(ticketId, "/suggest-priority", "priority suggestion");

export const useGenerateNextAction = (ticketId: string) =>
  useGenerate(ticketId, "/suggest-next-action", "next action");

export const useGenerateResponse = (ticketId: string) =>
  useGenerate(ticketId, "/suggest-response", "suggested response");

// ---------- accept / reject ----------

export function useAcceptSuggestion(ticketId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<AIAcceptResponse, ApiError, string>({
    mutationFn: (suggestionId) =>
      apiClient.post<AIAcceptResponse>(
        apiV1(`/ai/suggestions/${suggestionId}/accept`)
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: aiKeys.suggestionsForTicket(ticketId),
      });
    },
    onError: (error) => {
      toast({
        title: "Couldn't record acceptance",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export interface RejectVariables {
  suggestionId: string;
  reason?: string;
}

export function useRejectSuggestion(ticketId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<AIAcceptResponse, ApiError, RejectVariables>({
    mutationFn: ({ suggestionId, reason }) =>
      apiClient.post<AIAcceptResponse>(
        apiV1(`/ai/suggestions/${suggestionId}/reject`),
        { reason: reason ?? null }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: aiKeys.suggestionsForTicket(ticketId),
      });
    },
    onError: (error) => {
      toast({
        title: "Couldn't dismiss suggestion",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// ---------- generate all ----------

export function useGenerateAll(ticketId: string) {
  const summary = useGenerateSummary(ticketId);
  const classification = useGenerateClassification(ticketId);
  const priority = useGeneratePriority(ticketId);
  const nextAction = useGenerateNextAction(ticketId);
  const response = useGenerateResponse(ticketId);

  const isPending =
    summary.isPending ||
    classification.isPending ||
    priority.isPending ||
    nextAction.isPending ||
    response.isPending;

  const run = async () => {
    await Promise.allSettled([
      summary.mutateAsync(),
      classification.mutateAsync(),
      priority.mutateAsync(),
      nextAction.mutateAsync(),
      response.mutateAsync(),
    ]);
  };

  return { run, isPending };
}