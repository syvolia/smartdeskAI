"use client";

import {
  useMutation,
  useQueryClient,
  type QueryKey,
} from "@tanstack/react-query";

import { apiClient, apiV1, ApiError } from "@/lib/api-client";
import { useToast } from "@/hooks/use-toast";
import type {
  Ticket,
  TicketComment,
  TicketCommentListResponse,
  TicketListResponse,
} from "@/types/ticket";
import { ticketKeys } from "@/features/tickets/queries";

// ---------- utilities ----------

type Snapshot = ReadonlyArray<readonly [QueryKey, unknown]>;

interface MutationContext {
  snaps: Snapshot;
}

function patchTicketInLists(
  queryClient: ReturnType<typeof useQueryClient>,
  ticketId: string,
  patch: Partial<Ticket>
) {
  queryClient.setQueriesData<TicketListResponse>(
    { queryKey: ticketKeys.lists() },
    (current) => {
      if (!current) return current;
      return {
        ...current,
        items: current.items.map((t) =>
          t.id === ticketId ? { ...t, ...patch } : t
        ),
      };
    }
  );
}

function patchTicketDetail(
  queryClient: ReturnType<typeof useQueryClient>,
  ticketId: string,
  patch: Partial<Ticket>
) {
  queryClient.setQueryData<Ticket>(ticketKeys.detail(ticketId), (current) =>
    current ? { ...current, ...patch } : current
  );
}

function snapshot(
  keys: QueryKey[],
  queryClient: ReturnType<typeof useQueryClient>
): Snapshot {
  return keys.map((key) => [key, queryClient.getQueryData(key)] as const);
}

function restore(
  snaps: Snapshot,
  queryClient: ReturnType<typeof useQueryClient>
) {
  for (const [key, data] of snaps) {
    queryClient.setQueryData(key, data);
  }
}

// ---------- assign ----------

export interface AssignVariables {
  ticketId: string;
  assigned_agent_id: string | null;
  team_id?: string | null;
  note?: string | null;
}

export function useAssignTicket() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<Ticket, ApiError, AssignVariables, MutationContext>({
    mutationFn: ({ ticketId, ...body }) =>
      apiClient.post<Ticket>(apiV1(`/tickets/${ticketId}/assign`), body),
    onMutate: async ({ ticketId, assigned_agent_id }): Promise<MutationContext> => {
      const detailKey = ticketKeys.detail(ticketId);
      await queryClient.cancelQueries({ queryKey: detailKey });

      const snaps = snapshot([detailKey, ticketKeys.lists()], queryClient);
      const current = queryClient.getQueryData<Ticket>(detailKey);
      if (current) {
        patchTicketDetail(queryClient, ticketId, {
          assigned_agent: assigned_agent_id
            ? current.assigned_agent ?? null
            : null,
        });
      }
      return { snaps };
    },
    onError: (error, _vars, context) => {
      if (context) restore(context.snaps, queryClient);
      toast({
        title: "Couldn't update assignment",
        description: error.message,
        variant: "destructive",
      });
    },
    onSuccess: (ticket) => {
      patchTicketDetail(queryClient, ticket.id, ticket);
      patchTicketInLists(queryClient, ticket.id, ticket);
      queryClient.invalidateQueries({
        queryKey: ticketKeys.events(ticket.id),
      });
      toast({ title: "Ticket assigned", variant: "success" });
    },
  });
}

// ---------- status ----------

export interface StatusVariables {
  ticketId: string;
  status: Ticket["status"];
  note?: string | null;
}

export function useChangeTicketStatus() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<Ticket, ApiError, StatusVariables, MutationContext>({
    mutationFn: ({ ticketId, ...body }) =>
      apiClient.post<Ticket>(apiV1(`/tickets/${ticketId}/status`), body),
    onMutate: async ({ ticketId, status }): Promise<MutationContext> => {
      const detailKey = ticketKeys.detail(ticketId);
      await queryClient.cancelQueries({ queryKey: detailKey });
      const snaps = snapshot([detailKey, ticketKeys.lists()], queryClient);
      patchTicketDetail(queryClient, ticketId, { status });
      patchTicketInLists(queryClient, ticketId, { status });
      return { snaps };
    },
    onError: (error, _vars, context) => {
      if (context) restore(context.snaps, queryClient);
      toast({
        title: "Couldn't change status",
        description: error.message,
        variant: "destructive",
      });
    },
    onSuccess: (ticket) => {
      patchTicketDetail(queryClient, ticket.id, ticket);
      patchTicketInLists(queryClient, ticket.id, ticket);
      queryClient.invalidateQueries({
        queryKey: ticketKeys.events(ticket.id),
      });
      const label = ticket.status.replace(/_/g, " ").toLowerCase();
      toast({ title: `Ticket marked ${label}`, variant: "success" });
    },
  });
}

// ---------- priority ----------

export interface PriorityVariables {
  ticketId: string;
  priority: Ticket["priority"];
  note?: string | null;
}

export function useChangeTicketPriority() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<Ticket, ApiError, PriorityVariables, MutationContext>({
    mutationFn: ({ ticketId, ...body }) =>
      apiClient.post<Ticket>(apiV1(`/tickets/${ticketId}/priority`), body),
    onMutate: async ({ ticketId, priority }): Promise<MutationContext> => {
      const detailKey = ticketKeys.detail(ticketId);
      await queryClient.cancelQueries({ queryKey: detailKey });
      const snaps = snapshot([detailKey, ticketKeys.lists()], queryClient);
      patchTicketDetail(queryClient, ticketId, { priority });
      patchTicketInLists(queryClient, ticketId, { priority });
      return { snaps };
    },
    onError: (error, _vars, context) => {
      if (context) restore(context.snaps, queryClient);
      toast({
        title: "Couldn't change priority",
        description: error.message,
        variant: "destructive",
      });
    },
    onSuccess: (ticket) => {
      patchTicketDetail(queryClient, ticket.id, ticket);
      patchTicketInLists(queryClient, ticket.id, ticket);
      queryClient.invalidateQueries({
        queryKey: ticketKeys.events(ticket.id),
      });
      toast({ title: "Priority updated", variant: "success" });
    },
  });
}

// ---------- comment ----------

export interface CommentVariables {
  ticketId: string;
  body: string;
  is_internal: boolean;
}

export function useAddTicketComment() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<TicketComment, ApiError, CommentVariables, MutationContext>({
    mutationFn: ({ ticketId, ...body }) =>
      apiClient.post<TicketComment>(
        apiV1(`/tickets/${ticketId}/comments`),
        body
      ),
    onMutate: async ({
      ticketId,
      body,
      is_internal,
    }): Promise<MutationContext> => {
      const commentsKey = ticketKeys.comments(ticketId);
      await queryClient.cancelQueries({ queryKey: commentsKey });

      const snaps = snapshot([commentsKey], queryClient);

      const optimistic: TicketComment = {
        id: `optimistic-${Date.now()}`,
        organization_id: "",
        ticket_id: ticketId,
        author: null,
        body,
        is_internal,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      queryClient.setQueryData<TicketCommentListResponse>(
        commentsKey,
        (prev) => {
          if (!prev) return { items: [optimistic], total: 1 };
          return {
            items: [...prev.items, optimistic],
            total: prev.total + 1,
          };
        }
      );
      return { snaps };
    },
    onError: (error, _vars, context) => {
      if (context) restore(context.snaps, queryClient);
      toast({
        title: "Couldn't post comment",
        description: error.message,
        variant: "destructive",
      });
    },
    onSuccess: (comment) => {
      const commentsKey = ticketKeys.comments(comment.ticket_id);
      queryClient.setQueryData<TicketCommentListResponse>(
        commentsKey,
        (prev) => {
          if (!prev) return { items: [comment], total: 1 };
          const without = prev.items.filter(
            (c) => !c.id.startsWith("optimistic-")
          );
          return { items: [...without, comment], total: without.length + 1 };
        }
      );
      queryClient.invalidateQueries({
        queryKey: ticketKeys.events(comment.ticket_id),
      });
      queryClient.invalidateQueries({
        queryKey: ticketKeys.detail(comment.ticket_id),
      });
      toast({
        title: comment.is_internal ? "Internal note added" : "Reply sent",
        variant: "success",
      });
    },
  });
}

// ---------- update ----------

export interface UpdateVariables {
  ticketId: string;
  title?: string;
  description?: string;
  category_id?: string | null;
}

export function useUpdateTicket() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<Ticket, ApiError, UpdateVariables>({
    mutationFn: ({ ticketId, ...body }) =>
      apiClient.patch<Ticket>(apiV1(`/tickets/${ticketId}`), body),
    onSuccess: (ticket) => {
      patchTicketDetail(queryClient, ticket.id, ticket);
      patchTicketInLists(queryClient, ticket.id, ticket);
      queryClient.invalidateQueries({
        queryKey: ticketKeys.events(ticket.id),
      });
      toast({ title: "Ticket updated", variant: "success" });
    },
    onError: (error) => {
      toast({
        title: "Couldn't update ticket",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}