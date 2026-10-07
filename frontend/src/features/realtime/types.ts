export type RealtimeEventType =
  | "ticket.comment_created"
  | "ticket.status_changed"
  | "ticket.priority_changed"
  | "ticket.assigned"
  | "ticket.reassigned"
  | "ticket.created"
  | "ticket.updated"
  | "ticket.resolved"
  | "ticket.reopened"
  | "notification.created";

export interface RealtimeEvent {
  id: string;
  type: RealtimeEventType;
  organization_id: string;
  occurred_at: string;
  actor_user_id: string | null;
  ticket_id: string | null;
  ticket_customer_email: string | null;
  target_user_id: string | null;
  payload: Record<string, unknown>;
}

export type RealtimeFrame =
  | { kind: "hello"; user_id: string; org_id: string; role: string }
  | { kind: "pong" }
  | { kind: "event"; event: RealtimeEvent };