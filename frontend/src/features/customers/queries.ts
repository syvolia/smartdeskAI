"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient, apiV1 } from "@/lib/api-client";
import type { CustomerListResponse } from "@/types/customer";

export interface CustomerListParams {
  search?: string;
  page?: number;
  page_size?: number;
}

export const customerKeys = {
  all: ["customers"] as const,
  list: (params: CustomerListParams) =>
    [...customerKeys.all, "list", params] as const,
};

export function useCustomers(params: CustomerListParams) {
  return useQuery<CustomerListResponse, Error>({
    queryKey: customerKeys.list(params),
    queryFn: () =>
      apiClient.get<CustomerListResponse>(apiV1("/customers"), {
        query: {
          search: params.search,
          page: params.page,
          page_size: params.page_size,
        },
      }),
    placeholderData: (prev) => prev,
  });
}