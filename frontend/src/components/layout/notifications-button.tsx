"use client";

import { Bell } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useUnreadCount } from "@/features/notifications/queries";

export function NotificationsButton() {
  const { data } = useUnreadCount();
  const unread = data?.unread_count ?? 0;

  const label =
    unread > 0 ? `Notifications, ${unread} unread` : "Notifications";

  return (
    <Button
      asChild
      variant="ghost"
      size="icon"
      className="relative"
      aria-label={label}
    >
      <Link href="/notifications">
        <Bell className="h-4 w-4" aria-hidden="true" />
        {unread > 0 ? (
          <span
            aria-hidden="true"
            className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-none text-destructive-foreground"
          >
            {unread > 99 ? "99+" : unread}
          </span>
        ) : null}
      </Link>
    </Button>
  );
}
