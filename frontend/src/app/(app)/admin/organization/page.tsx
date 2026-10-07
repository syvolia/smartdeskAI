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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdateOrganization } from "@/features/admin/mutations";
import { useOrganizationProfile } from "@/features/admin/queries";

export default function OrganizationPage() {
  const query = useOrganizationProfile();
  const update = useUpdateOrganization();

  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("UTC");

  useEffect(() => {
    if (query.data) {
      setName(query.data.name);
      const tz = query.data.settings?.timezone;
      if (typeof tz === "string") setTimezone(tz);
    }
  }, [query.data]);

  if (query.isLoading) return <LoadingState variant="page" />;
  if (query.isError) {
    return (
      <ErrorState
        title="Couldn't load organization"
        onRetry={() => query.refetch()}
      />
    );
  }
  if (!query.data) return null;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    update.mutate({ name, settings: { timezone } });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Organization profile</CardTitle>
        <CardDescription>
          Name and general settings for {query.data.slug}.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4 max-w-md">
          <div className="space-y-1.5">
            <Label htmlFor="org-name">Organization name</Label>
            <Input
              id="org-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="org-tz">Default timezone</Label>
            <Input
              id="org-tz"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="America/New_York"
            />
          </div>

          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
