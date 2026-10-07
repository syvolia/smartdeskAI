export type NotificationType =
  | "TICKET_ASSIGNED"
  | "TICKET_REASSIGNED"
  | "TICKET_COMMENT"
  | "TICKET_RESOLVED"
  | "TICKET_REOPENED"
  | "TICKET_UPDATED"
  | "SLA_WARNING"
  | "SLA_BREACHED"
  | "MENTION";

export interface Notification {
  id: string;
  organization_id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MarkReadResponse {
  notification: Notification;
}

export interface MarkAllReadResponse {
  updated: number;
  unread_count: number;
}