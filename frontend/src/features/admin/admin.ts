import type { UserRole } from "@/types/auth";
import type { TicketPriority } from "@/types/ticket";

export interface OrganizationProfile {
  id: string;
  name: string;
  slug: string;
  plan: string;
  settings: Record<string, unknown>;
  ai_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AdminOverview {
  users: number;
  agents: number;
  teams: number;
  categories: number;
  slas: number;
  kb_articles: number;
  kb_published: number;
  plan: string;
  ai_enabled: boolean;
}

export interface AdminUser {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUserList {
  items: AdminUser[];
  total: number;
}

export interface TeamMemberSummary {
  user_id: string;
  full_name: string;
  email: string;
  role: UserRole;
  role_in_team: string | null;
}

export interface Team {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  members: TeamMemberSummary[];
  created_at: string;
  updated_at: string;
}

export interface TeamList {
  items: Team[];
  total: number;
}

export interface TicketCategory {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketCategoryList {
  items: TicketCategory[];
  total: number;
}

export interface SLA {
  id: string;
  organization_id: string;
  name: string;
  priority: TicketPriority;
  first_response_minutes: number;
  resolution_minutes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SLAList {
  items: SLA[];
  total: number;
}

export interface ChannelPreference {
  email: boolean;
  in_app: boolean;
}

export interface NotificationPreferences {
  user_id: string;
  organization_id: string;
  prefs: Record<string, ChannelPreference>;
}

export interface KBCategory {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface KBCategoryList {
  items: KBCategory[];
  total: number;
}

export interface KBArticle {
  id: string;
  organization_id: string;
  category_id: string | null;
  author_user_id: string | null;
  title: string;
  slug: string;
  body: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KBArticleList {
  items: KBArticle[];
  total: number;
}