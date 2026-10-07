"use client";

import {
  Bell,
  Building2,
  LayoutDashboard,
  Sparkles,
  Tags,
  Timer,
  UserCog,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface AdminLink {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
}

const LINKS: AdminLink[] = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/admin/organization", label: "Organization", icon: Building2 },
  { href: "/admin/users", label: "Users & agents", icon: UserCog },
  { href: "/admin/teams", label: "Teams", icon: UsersRound },
  { href: "/admin/categories", label: "Ticket categories", icon: Tags },
  { href: "/admin/slas", label: "SLAs", icon: Timer },
  { href: "/admin/ai", label: "AI", icon: Sparkles },
  { href: "/admin/notifications", label: "Notifications", icon: Bell },
];

export function AdminNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Admin sections"
      className="lg:sticky lg:top-20 lg:self-start"
    >
      <ul className="space-y-0.5">
        {LINKS.map((l) => {
          const active = l.exact
            ? pathname === l.href
            : pathname.startsWith(l.href);
          const Icon = l.icon;
          return (
            <li key={l.href}>
              <Link
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {l.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}