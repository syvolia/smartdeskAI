import type { Metadata } from "next";

import { TicketDetailView } from "@/features/tickets/ticket-detail-view";

export const metadata: Metadata = { title: "Ticket" };

export default function TicketDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <TicketDetailView ticketId={params.id} />;
}
