"use client";

import { Menu } from "lucide-react";
import { useState } from "react";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { RealtimeStatus } from "@/components/layout/realtime-status";
import { SidebarBrand, SidebarNav } from "@/components/layout/sidebar";
import { UserMenu } from "@/components/layout/user-menu";
import { NotificationsButton } from "@/components/layout/notifications-button";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

export function TopNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 lg:px-6">
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </Button>
        </SheetTrigger>
        <SheetContent
          side="left"
          className="flex w-72 flex-col border-sidebar-border bg-sidebar p-0 text-sidebar-foreground"
        >
          <SidebarBrand />
          <SidebarNav onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="min-w-0 flex-1">
        <Breadcrumbs />
      </div>

      <div className="flex items-center gap-1">
        <RealtimeStatus />
        <NotificationsButton />
        <UserMenu />
      </div>
    </header>
  );
}
