"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient, apiV1 } from "@/lib/api-client";
import type {
  NotificationListResponse,
  UnreadCountResponse,
} from "@/types/notification";

export const notificationKeys = {
  all: ["notifications"] as const,
  list: (params: { unreadOnly?: boolean; page?: number }) =>
    [...notificationKeys.all, "list", params] as const,
  unreadCount: () => [...notificationKeys.all, "unread-count"] as const,
};

export function useNotifications(params: {
  unreadOnly?: boolean;
  page?: number;
  pageSize?: number;
}) {
  return useQuery<NotificationListResponse, Error>({
    queryKey: notificationKeys.list({
      unreadOnly: params.unreadOnly,
      page: params.page,
    }),
    queryFn: () =>
      apiClient.get<NotificationListResponse>(apiV1("/notifications"), {
        query: {
          unread_only: params.unreadOnly ? "true" : undefined,
          page: params.page,
          page_size: params.pageSize,
        },
      }),
    staleTime: 15_000,
  });
}

export function useUnreadCount() {
  return useQuery<UnreadCountResponse, Error>({
    queryKey: notificationKeys.unreadCount(),
    queryFn: () =>
      apiClient.get<UnreadCountResponse>(apiV1("/notifications/unread-count")),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}