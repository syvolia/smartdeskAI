import type { Metadata } from "next";

import { TicketsListView } from "@/features/tickets/tickets-list-view";

export const metadata: Metadata = { title: "Tickets" };

export default function TicketsPage() {
  return <TicketsListView />;
}
