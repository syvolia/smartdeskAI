import {
  BarChart3,
  Bell,
  BookOpen,
  Building2,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Sparkles,
  Tags,
  Ticket,
  Timer,
  UserCog,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import type { UserRole } from "@/types/auth";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Only show this item if the current user's role is in this list. */
  roles?: UserRole[];
}

export interface NavSection {
  title: string;
  items: NavItem[];
  roles?: UserRole[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Workspace",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/tickets", label: "Tickets", icon: Ticket },
      {
        href: "/customers",
        label: "Customers",
        icon: Users,
        roles: ["ADMIN", "AGENT"],
      },
    ],
  },
  {
    title: "Knowledge",
    items: [
      { href: "/knowledge-base", label: "Knowledge base", icon: BookOpen },
    ],
  },
  {
    title: "Insights",
    roles: ["ADMIN", "AGENT"],
    items: [
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/notifications", label: "Notifications", icon: Bell },
    ],
  },
  {
    title: "Account",
    roles: ["CUSTOMER"],
    items: [
      { href: "/notifications", label: "Notifications", icon: Bell },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
  {
    title: "Admin",
    roles: ["ADMIN"],
    items: [
      { href: "/admin", label: "Overview", icon: ShieldCheck },
      { href: "/admin/organization", label: "Organization", icon: Building2 },
      { href: "/admin/users", label: "Users & agents", icon: UserCog },
      { href: "/admin/teams", label: "Teams", icon: UsersRound },
      { href: "/admin/categories", label: "Ticket categories", icon: Tags },
      { href: "/admin/slas", label: "SLAs", icon: Timer },
      { href: "/admin/ai", label: "AI configuration", icon: Sparkles },
      { href: "/admin/notifications", label: "Notifications", icon: Bell },
      { href: "/settings", label: "My settings", icon: Settings },
    ],
  },
];

export function navLabelForPath(pathname: string): string | null {
  for (const section of NAV_SECTIONS) {
    for (const item of section.items) {
      if (pathname === item.href || pathname.startsWith(`${item.href}/`)) {
        return item.label;
      }
    }
  }
  return null;
}

export function canSeeItem(item: NavItem, role: UserRole): boolean {
  if (!item.roles) return true;
  return item.roles.includes(role);
}

export function canSeeSection(section: NavSection, role: UserRole): boolean {
  if (section.roles && !section.roles.includes(role)) return false;
  return section.items.some((item) => canSeeItem(item, role));
}