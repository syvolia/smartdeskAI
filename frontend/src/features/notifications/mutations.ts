"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient, apiV1, ApiError } from "@/lib/api-client";
import { useToast } from "@/hooks/use-toast";
import { notificationKeys } from "@/features/notifications/queries";
import type {
  MarkAllReadResponse,
  MarkReadResponse,
} from "@/types/notification";

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<MarkReadResponse, ApiError, string>({
    mutationFn: (id) =>
      apiClient.patch<MarkReadResponse>(apiV1(`/notifications/${id}/read`)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
    onError: (error) => {
      toast({
        title: "Couldn't mark as read",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<MarkAllReadResponse, ApiError, void>({
    mutationFn: () =>
      apiClient.patch<MarkAllReadResponse>(apiV1("/notifications/read-all")),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
      toast({
        title: `Marked ${data.updated} as read`,
        variant: "success",
      });
    },
    onError: (error) => {
      toast({
        title: "Couldn't mark all as read",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}