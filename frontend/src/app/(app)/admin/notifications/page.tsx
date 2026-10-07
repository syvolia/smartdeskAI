"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useUpdateMyNotificationPreferences } from "@/features/admin/mutations";
import { useMyNotificationPreferences } from "@/features/admin/queries";

const EVENT_TYPES = [
  { key: "TICKET_ASSIGNED", label: "Ticket assigned to me" },
  { key: "TICKET_REASSIGNED", label: "Ticket reassigned" },
  { key: "TICKET_COMMENT", label: "New comment on my tickets" },
  { key: "TICKET_RESOLVED", label: "Ticket resolved" },
  { key: "TICKET_REOPENED", label: "Ticket reopened" },
  { key: "SLA_WARNING", label: "SLA approaching breach" },
  { key: "SLA_BREACHED", label: "SLA breached" },
] as const;

type Prefs = Record<string, { email: boolean; in_app: boolean }>;

function defaults(): Prefs {
  const out: Prefs = {};
  for (const e of EVENT_TYPES) {
    out[e.key] = { email: true, in_app: true };
  }
  return out;
}

export default function NotificationPreferencesPage() {
  const query = useMyNotificationPreferences();
  const update = useUpdateMyNotificationPreferences();
  const [prefs, setPrefs] = useState<Prefs>(defaults);

  useEffect(() => {
    if (query.data) {
      setPrefs({ ...defaults(), ...query.data.prefs });
    }
  }, [query.data]);

  if (query.isLoading) return <LoadingState variant="page" />;
  if (query.isError) {
    return (
      <ErrorState
        title="Couldn't load preferences"
        onRetry={() => query.refetch()}
      />
    );
  }

  const toggle = (eventKey: string, channel: "email" | "in_app") => {
    setPrefs((p) => ({
      ...p,
      [eventKey]: { ...p[eventKey], [channel]: !p[eventKey][channel] },
    }));
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    update.mutate(prefs);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notification preferences</CardTitle>
        <CardDescription>
          Choose how you want to be notified for each event type.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit}>
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th scope="col" className="py-2 pr-4">
                  Event
                </th>
                <th scope="col" className="py-2 pr-4 text-center">
                  In-app
                </th>
                <th scope="col" className="py-2 text-center">
                  Email
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {EVENT_TYPES.map((e) => (
                <tr key={e.key}>
                  <td className="py-3 pr-4">{e.label}</td>
                  <td className="py-3 pr-4 text-center">
                    <input
                      type="checkbox"
                      aria-label={`In-app notifications for ${e.label}`}
                      checked={prefs[e.key]?.in_app ?? true}
                      onChange={() => toggle(e.key, "in_app")}
                      className="h-4 w-4 rounded border-input text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    />
                  </td>
                  <td className="py-3 text-center">
                    <input
                      type="checkbox"
                      aria-label={`Email notifications for ${e.label}`}
                      checked={prefs[e.key]?.email ?? true}
                      onChange={() => toggle(e.key, "email")}
                      className="h-4 w-4 rounded border-input text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-4">
            <Button type="submit" disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save preferences"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
