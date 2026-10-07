"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient, apiV1, ApiError } from "@/lib/api-client";
import { adminKeys } from "@/features/admin/queries";
import { useToast } from "@/hooks/use-toast";
import type {
  AdminUser,
  NotificationPreferences,
  OrganizationProfile,
  SLA,
  Team,
  TicketCategory,
} from "@/types/admin";

// ---------- organization ----------

export function useUpdateOrganization() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    OrganizationProfile,
    ApiError,
    { name?: string; plan?: string; settings?: Record<string, unknown> }
  >({
    mutationFn: (payload) =>
      apiClient.patch<OrganizationProfile>(
        apiV1("/admin/organization"),
        payload
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.organization() });
      toast({ title: "Organization updated", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't update organization",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// ---------- users ----------

export function useCreateUser() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    AdminUser,
    ApiError,
    { email: string; full_name: string; role: string; password: string }
  >({
    mutationFn: (payload) =>
      apiClient.post<AdminUser>(apiV1("/admin/users"), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users({}) });
      queryClient.invalidateQueries({ queryKey: adminKeys.overview() });
      toast({ title: "User created", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't create user",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    AdminUser,
    ApiError,
    { id: string; full_name?: string; role?: string; is_active?: boolean }
  >({
    mutationFn: ({ id, ...payload }) =>
      apiClient.patch<AdminUser>(apiV1(`/admin/users/${id}`), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users({}) });
      toast({ title: "User updated", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't update user",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// ---------- teams ----------

export function useCreateTeam() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    Team,
    ApiError,
    { name: string; description?: string | null }
  >({
    mutationFn: (payload) =>
      apiClient.post<Team>(apiV1("/admin/teams"), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.teams() });
      toast({ title: "Team created", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't create team",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useDeleteTeam() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) =>
      apiClient.delete<void>(apiV1(`/admin/teams/${id}`)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.teams() });
      toast({ title: "Team deleted", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't delete team",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// ---------- categories ----------

export function useCreateCategory() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    TicketCategory,
    ApiError,
    { name: string; description?: string | null }
  >({
    mutationFn: (payload) =>
      apiClient.post<TicketCategory>(
        apiV1("/admin/ticket-categories"),
        payload
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.categories() });
      toast({ title: "Category created", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't create category",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) =>
      apiClient.delete<void>(apiV1(`/admin/ticket-categories/${id}`)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.categories() });
      toast({ title: "Category deleted", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't delete category",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// ---------- SLAs ----------

export function useCreateSLA() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    SLA,
    ApiError,
    {
      name: string;
      priority: string;
      first_response_minutes: number;
      resolution_minutes: number;
      is_active: boolean;
    }
  >({
    mutationFn: (payload) =>
      apiClient.post<SLA>(apiV1("/admin/slas"), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.slas() });
      toast({ title: "SLA created", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't create SLA",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useDeleteSLA() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => apiClient.delete<void>(apiV1(`/admin/slas/${id}`)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.slas() });
      toast({ title: "SLA deleted", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't delete SLA",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// ---------- AI config ----------

export function useUpdateAIConfig() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    OrganizationProfile,
    ApiError,
    Record<string, unknown>
  >({
    mutationFn: (payload) =>
      apiClient.patch<OrganizationProfile>(apiV1("/admin/ai-config"), {
        ai_config: payload,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.aiConfig() });
      queryClient.invalidateQueries({ queryKey: adminKeys.overview() });
      toast({ title: "AI configuration saved", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't save AI configuration",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// ---------- notification preferences ----------

export function useUpdateMyNotificationPreferences() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    NotificationPreferences,
    ApiError,
    Record<string, { email: boolean; in_app: boolean }>
  >({
    mutationFn: (prefs) =>
      apiClient.put<NotificationPreferences>(
        apiV1("/admin/notification-preferences/me"),
        { prefs }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: adminKeys.notificationPrefs(),
      });
      toast({ title: "Preferences saved", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't save preferences",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
// ---------- team members ----------

export function useAddTeamMember() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    Team,
    ApiError,
    { teamId: string; userId: string; role_in_team?: string | null }
  >({
    mutationFn: ({ teamId, userId, role_in_team }) =>
      apiClient.post<Team>(apiV1(`/admin/teams/${teamId}/members`), {
        user_id: userId,
        role_in_team: role_in_team ?? null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.teams() });
      toast({ title: "Member added", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't add member",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useRemoveTeamMember() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation<
    Team,
    ApiError,
    { teamId: string; userId: string }
  >({
    mutationFn: ({ teamId, userId }) =>
      apiClient.delete<Team>(
        apiV1(`/admin/teams/${teamId}/members/${userId}`)
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.teams() });
      toast({ title: "Member removed", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't remove member",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}