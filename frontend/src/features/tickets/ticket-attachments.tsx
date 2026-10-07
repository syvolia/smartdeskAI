"use client";

import { Paperclip } from "lucide-react";

interface TicketAttachmentsProps {
  ticketId: string;
}

export function TicketAttachments({
  ticketId: _ticketId,
}: TicketAttachmentsProps) {
  // The backend doesn't yet expose an attachment listing endpoint.
  // When it lands, swap this for a useTicketAttachments query and
  // render a list with download links (presigned URLs).
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-4 py-10 text-center">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Paperclip className="h-4 w-4" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium">No attachments yet</p>
      <p className="mt-1 max-w-sm text-xs text-muted-foreground">
        Files attached to comments and the ticket will appear here once
        attachment uploads ship.
      </p>
    </div>
  );
}
