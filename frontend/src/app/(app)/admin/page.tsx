"use client";

import {
  Building2,
  Sparkles,
  Tags,
  Timer,
  UserCog,
  UsersRound,
  BookOpen,
} from "lucide-react";

import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAdminOverview } from "@/features/admin/queries";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export default function AdminOverviewPage() {
  const query = useAdminOverview();

  if (query.isLoading) return <LoadingState variant="page" />;
  if (query.isError) {
    return (
      <ErrorState
        title="Couldn't load admin overview"
        onRetry={() => query.refetch()}
      />
    );
  }
  if (!query.data) return null;

  const d = query.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Organization at a glance</CardTitle>
          <CardDescription>
            Plan: <Badge variant="neutral">{d.plan}</Badge> · AI:{" "}
            <Badge variant={d.ai_enabled ? "success" : "neutral"}>
              {d.ai_enabled ? "enabled" : "disabled"}
            </Badge>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            <Stat label="Users" value={d.users} />
            <Stat label="Agents" value={d.agents} />
            <Stat label="Teams" value={d.teams} />
            <Stat label="Categories" value={d.categories} />
            <Stat label="SLAs" value={d.slas} />
            <Stat label="KB articles" value={d.kb_articles} />
            <Stat label="KB published" value={d.kb_published} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickLink
          href="/admin/users"
          icon={UserCog}
          title="Users & agents"
          description="Invite teammates, adjust roles, deactivate accounts."
        />
        <QuickLink
          href="/admin/teams"
          icon={UsersRound}
          title="Teams"
          description="Group agents and route ticket work by team."
        />
        <QuickLink
          href="/admin/categories"
          icon={Tags}
          title="Ticket categories"
          description="Control the classification taxonomy."
        />
        <QuickLink
          href="/admin/slas"
          icon={Timer}
          title="SLA policies"
          description="Define first-response and resolution targets by priority."
        />
        <QuickLink
          href="/admin/ai"
          icon={Sparkles}
          title="AI configuration"
          description="Toggle AI features and set confidence thresholds."
        />
        <QuickLink
          href="/knowledge-base"
          icon={BookOpen}
          title="Knowledge base"
          description="Write and publish help articles."
        />
      </div>
    </div>
  );
}

function QuickLink({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <a
      href={href}
      className="rounded-lg border bg-card p-4 transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <p className="text-sm font-semibold">{title}</p>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </a>
  );
}
