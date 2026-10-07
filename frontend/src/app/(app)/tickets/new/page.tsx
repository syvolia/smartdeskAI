import type { Metadata } from "next";

import { CreateTicketView } from "@/features/tickets/create-ticket-view";

export const metadata: Metadata = { title: "New ticket" };

export default function NewTicketPage() {
  return <CreateTicketView />;
}
