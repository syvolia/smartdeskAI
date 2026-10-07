"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient, apiV1 } from "@/lib/api-client";
import type { AnalyticsDashboard } from "@/types/analytics";

export interface DashboardParams {
  date_from?: string;
  date_to?: string;
  granularity?: "day" | "week" | "month";
}

export const analyticsKeys = {
  all: ["analytics"] as const,
  dashboard: (params: DashboardParams) =>
    [...analyticsKeys.all, "dashboard", params] as const,
};

export function useAnalyticsDashboard(params: DashboardParams) {
  return useQuery<AnalyticsDashboard, Error>({
    queryKey: analyticsKeys.dashboard(params),
    queryFn: () =>
      apiClient.get<AnalyticsDashboard>(apiV1("/analytics/dashboard"), {
        query: {
          date_from: params.date_from,
          date_to: params.date_to,
          granularity: params.granularity,
        },
      }),
    staleTime: 30_000,
  });
}