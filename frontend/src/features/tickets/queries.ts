"use client";

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";

import { apiClient, apiV1 } from "@/lib/api-client";
import type {
  Ticket,
  TicketCommentListResponse,
  TicketEventListResponse,
  TicketListResponse,
  TicketPriority,
  TicketStatus,
} from "@/types/ticket";

export const ticketKeys = {
  all: ["tickets"] as const,
  lists: () => [...ticketKeys.all, "list"] as const,
  list: (params: TicketListParams) =>
    [...ticketKeys.lists(), params] as const,
  details: () => [...ticketKeys.all, "detail"] as const,
  detail: (id: string) => [...ticketKeys.details(), id] as const,
  comments: (id: string) => [...ticketKeys.detail(id), "comments"] as const,
  events: (id: string) => [...ticketKeys.detail(id), "events"] as const,
};

export interface TicketListParams {
  search?: string;
  status?: TicketStatus[];
  priority?: TicketPriority[];
  assigned_agent_id?: string;
  team_id?: string;
  customer_id?: string;
  category_id?: string;
  created_from?: string;
  created_to?: string;
  sort?: string;
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

function toQuery(params: TicketListParams) {
  const query: Record<string, string | number | string[] | undefined> = {};
  if (params.search) query.search = params.search;
  if (params.status?.length) query.status = params.status;
  if (params.priority?.length) query.priority = params.priority;
  if (params.assigned_agent_id) query.assigned_agent_id = params.assigned_agent_id;
  if (params.team_id) query.team_id = params.team_id;
  if (params.customer_id) query.customer_id = params.customer_id;
  if (params.category_id) query.category_id = params.category_id;
  if (params.created_from) query.created_from = params.created_from;
  if (params.created_to) query.created_to = params.created_to;
  if (params.sort) query.sort = params.sort;
  if (params.order) query.order = params.order;
  if (params.page) query.page = params.page;
  if (params.page_size) query.page_size = params.page_size;
  return query;
}

export function useTickets(
  params: TicketListParams,
  options?: Omit<
    UseQueryOptions<TicketListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<TicketListResponse, Error>({
    queryKey: ticketKeys.list(params),
    queryFn: () =>
      apiClient.get<TicketListResponse>(apiV1("/tickets"), {
        query: toQuery(params) as Record<string, string | number | undefined>,
      }),
    placeholderData: (prev) => prev,
    ...options,
  });
}

export function useTicket(
  id: string,
  options?: Omit<UseQueryOptions<Ticket, Error>, "queryKey" | "queryFn">
) {
  return useQuery<Ticket, Error>({
    queryKey: ticketKeys.detail(id),
    queryFn: () => apiClient.get<Ticket>(apiV1(`/tickets/${id}`)),
    enabled: Boolean(id),
    ...options,
  });
}

export function useTicketComments(
  id: string,
  options?: Omit<
    UseQueryOptions<TicketCommentListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<TicketCommentListResponse, Error>({
    queryKey: ticketKeys.comments(id),
    queryFn: () =>
      apiClient.get<TicketCommentListResponse>(
        apiV1(`/tickets/${id}/comments`)
      ),
    enabled: Boolean(id),
    ...options,
  });
}

export function useTicketEvents(
  id: string,
  options?: Omit<
    UseQueryOptions<TicketEventListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<TicketEventListResponse, Error>({
    queryKey: ticketKeys.events(id),
    queryFn: () =>
      apiClient.get<TicketEventListResponse>(
        apiV1(`/tickets/${id}/events`)
      ),
    enabled: Boolean(id),
    ...options,
  });
}