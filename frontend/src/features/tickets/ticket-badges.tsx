import { Badge } from "@/components/ui/badge";
import type { TicketPriority, TicketStatus } from "@/types/ticket";

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const variant =
    priority === "URGENT"
      ? "danger"
      : priority === "HIGH"
      ? "warning"
      : priority === "LOW"
      ? "neutral"
      : "info";
  return <Badge variant={variant}>{priority}</Badge>;
}

export function StatusBadge({ status }: { status: TicketStatus }) {
  const variant =
    status === "RESOLVED" || status === "CLOSED"
      ? "success"
      : status === "IN_PROGRESS"
      ? "info"
      : status === "WAITING_CUSTOMER"
      ? "warning"
      : "neutral";
  return <Badge variant={variant}>{status.replace(/_/g, " ")}</Badge>;
}

export function SlaBadge({
  breached,
  due,
}: {
  breached: boolean;
  due: string | null;
}) {
  if (breached) return <Badge variant="danger">Breached</Badge>;
  if (!due) return <Badge variant="neutral">No SLA</Badge>;
  return <Badge variant="success">On track</Badge>;
}
