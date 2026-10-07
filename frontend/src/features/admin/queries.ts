"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient, apiV1 } from "@/lib/api-client";
import type {
  AdminOverview,
  AdminUser,
  AdminUserList,
  KBCategory,
  KBCategoryList,
  KBArticle,
  KBArticleList,
  NotificationPreferences,
  OrganizationProfile,
  SLA,
  SLAList,
  Team,
  TeamList,
  TicketCategory,
  TicketCategoryList,
} from "@/types/admin";

export const adminKeys = {
  all: ["admin"] as const,
  overview: () => [...adminKeys.all, "overview"] as const,
  organization: () => [...adminKeys.all, "organization"] as const,
  users: (params: { role?: string; search?: string }) =>
    [...adminKeys.all, "users", params] as const,
  teams: () => [...adminKeys.all, "teams"] as const,
  categories: () => [...adminKeys.all, "categories"] as const,
  slas: () => [...adminKeys.all, "slas"] as const,
  aiConfig: () => [...adminKeys.all, "ai-config"] as const,
  notificationPrefs: () => [...adminKeys.all, "notification-prefs"] as const,
  kbCategories: () => [...adminKeys.all, "kb-categories"] as const,
  kbArticles: () => [...adminKeys.all, "kb-articles"] as const,
};

export function useAdminOverview() {
  return useQuery<AdminOverview, Error>({
    queryKey: adminKeys.overview(),
    queryFn: () =>
      apiClient.get<AdminOverview>(apiV1("/admin/overview")),
  });
}

export function useOrganizationProfile() {
  return useQuery<OrganizationProfile, Error>({
    queryKey: adminKeys.organization(),
    queryFn: () =>
      apiClient.get<OrganizationProfile>(apiV1("/admin/organization")),
  });
}

export function useAdminUsers(params: { role?: string; search?: string } = {}) {
  return useQuery<AdminUserList, Error>({
    queryKey: adminKeys.users(params),
    queryFn: () =>
      apiClient.get<AdminUserList>(apiV1("/admin/users"), {
        query: { role: params.role, search: params.search },
      }),
  });
}

export function useAdminTeams() {
  return useQuery<TeamList, Error>({
    queryKey: adminKeys.teams(),
    queryFn: () => apiClient.get<TeamList>(apiV1("/admin/teams")),
  });
}

export function useAdminCategories() {
  return useQuery<TicketCategoryList, Error>({
    queryKey: adminKeys.categories(),
    queryFn: () =>
      apiClient.get<TicketCategoryList>(apiV1("/admin/ticket-categories")),
  });
}

export function useAdminSlas() {
  return useQuery<SLAList, Error>({
    queryKey: adminKeys.slas(),
    queryFn: () => apiClient.get<SLAList>(apiV1("/admin/slas")),
  });
}

export function useAIConfig() {
  return useQuery<Record<string, unknown>, Error>({
    queryKey: adminKeys.aiConfig(),
    queryFn: () =>
      apiClient.get<Record<string, unknown>>(apiV1("/admin/ai-config")),
  });
}

export function useMyNotificationPreferences() {
  return useQuery<NotificationPreferences, Error>({
    queryKey: adminKeys.notificationPrefs(),
    queryFn: () =>
      apiClient.get<NotificationPreferences>(
        apiV1("/admin/notification-preferences/me")
      ),
  });
}

export type {
  AdminOverview,
  AdminUser,
  KBCategory,
  KBArticle,
  NotificationPreferences,
  OrganizationProfile,
  SLA,
  Team,
  TicketCategory,
};