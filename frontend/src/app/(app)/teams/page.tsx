import type { Metadata } from "next";
import { UsersRound } from "lucide-react";

import { PlaceholderPage } from "@/components/layout/placeholder-page";

export const metadata: Metadata = { title: "Teams" };

export default function TeamsPage() {
  return (
    <PlaceholderPage
      title="Teams"
      description="Organize agents into teams and route work where it belongs."
      icon={UsersRound}
      emptyTitle="Team management coming next"
      emptyDescription="Create teams, assign members, and configure routing rules here."
    />
  );
}
