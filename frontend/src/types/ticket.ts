export type TicketStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "WAITING_CUSTOMER"
  | "RESOLVED"
  | "CLOSED";

export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type TicketSource = "WEB" | "EMAIL" | "CHAT" | "PHONE" | "API";

export interface TicketCustomerSummary {
  id: string;
  email: string;
  full_name: string;
}

export interface TicketUserSummary {
  id: string;
  email: string;
  full_name: string;
  role: "ADMIN" | "AGENT" | "CUSTOMER";
}

export interface TicketSlaResponse {
  policy_id: string | null;
  policy_name: string | null;
  first_response_due_at: string | null;
  first_response_at: string | null;
  resolution_due_at: string | null;
  resolved_at: string | null;
  first_response_breached: boolean;
  resolution_breached: boolean;
  sla_breached: boolean;
  first_response_time_seconds: number | null;
  resolution_time_seconds: number | null;
}

export interface Ticket {
  id: string;
  organization_id: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  source: TicketSource;
  customer: TicketCustomerSummary;
  assigned_agent: TicketUserSummary | null;
  team: { id: string; name: string } | null;
  category: { id: string; name: string } | null;
  sla: TicketSlaResponse | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TicketComment {
  id: string;
  organization_id: string;
  ticket_id: string;
  author: TicketUserSummary | null;
  body: string;
  is_internal: boolean;
  created_at: string;
  updated_at: string;
}

export interface TicketCommentListResponse {
  items: TicketComment[];
  total: number;
}

export type TicketEventType =
  | "TICKET_CREATED"
  | "TICKET_UPDATED"
  | "TICKET_ASSIGNED"
  | "TICKET_REASSIGNED"
  | "STATUS_CHANGED"
  | "PRIORITY_CHANGED"
  | "COMMENT_ADDED"
  | "TICKET_RESOLVED"
  | "TICKET_REOPENED"
  | "TICKET_CLOSED"
  | "SLA_POLICY_APPLIED"
  | "SLA_BREACHED";

export interface TicketEvent {
  id: string;
  organization_id: string;
  ticket_id: string;
  actor: TicketUserSummary | null;
  event_type: TicketEventType;
  from_value: string | null;
  to_value: string | null;
  note: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface TicketEventListResponse {
  items: TicketEvent[];
  total: number;
}