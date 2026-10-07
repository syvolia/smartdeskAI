"use client";

import { Plus, Trash2, UserPlus, X } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAddTeamMember,
  useCreateTeam,
  useDeleteTeam,
  useRemoveTeamMember,
} from "@/features/admin/mutations";
import { useAdminTeams, useAdminUsers } from "@/features/admin/queries";
import type { Team, TeamMemberSummary } from "@/types/admin";

export default function TeamsPage() {
  const query = useAdminTeams();
  const create = useCreateTeam();
  const del = useDeleteTeam();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(
      { name, description: description || null },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
        },
      },
    );
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Create team</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={onSubmit}
            className="grid gap-3 sm:grid-cols-[1fr_2fr_auto] sm:items-end"
          >
            <div className="space-y-1.5">
              <Label htmlFor="team-name">Name</Label>
              <Input
                id="team-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="team-desc">Description</Label>
              <Input
                id="team-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={create.isPending}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add
            </Button>
          </form>
        </CardContent>
      </Card>

      {query.isLoading ? (
        <LoadingState variant="list" rows={4} />
      ) : query.isError ? (
        <ErrorState
          title="Couldn't load teams"
          onRetry={() => query.refetch()}
        />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState
          title="No teams yet"
          description="Create your first team to start routing tickets."
        />
      ) : query.data ? (
        <ul className="space-y-3">
          {query.data.items.map((team) => (
            <li key={team.id}>
              <TeamCard team={team} onDelete={() => del.mutate(team.id)} />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function TeamCard({ team, onDelete }: { team: Team; onDelete: () => void }) {
  const addMember = useAddTeamMember();
  const removeMember = useRemoveTeamMember();

  const agentsQuery = useAdminUsers({ role: "AGENT" });
  const adminsQuery = useAdminUsers({ role: "ADMIN" });

  const [showAdd, setShowAdd] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>("");

  // Eligible users: agents and admins, minus anyone already on this team.
  const existingIds = new Set(team.members.map((m) => m.user_id));
  const eligible = [
    ...(agentsQuery.data?.items ?? []),
    ...(adminsQuery.data?.items ?? []),
  ].filter((u) => !existingIds.has(u.id));

  const onAdd = () => {
    if (!selectedUserId) return;
    addMember.mutate(
      { teamId: team.id, userId: selectedUserId },
      {
        onSuccess: () => {
          setSelectedUserId("");
          setShowAdd(false);
        },
      },
    );
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold">{team.name}</p>
              <Badge variant="neutral">
                {team.members.length} member
                {team.members.length === 1 ? "" : "s"}
              </Badge>
            </div>
            {team.description ? (
              <p className="mt-1 text-sm text-muted-foreground">
                {team.description}
              </p>
            ) : null}
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Delete team ${team.name}`}
            onClick={() => {
              if (
                window.confirm(
                  `Delete team "${team.name}"? This cannot be undone.`,
                )
              ) {
                onDelete();
              }
            }}
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </div>

        <div className="mt-3">
          {team.members.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No members yet. Add someone to route work to this team.
            </p>
          ) : (
            <ul className="flex flex-wrap gap-1.5">
              {team.members.map((m) => (
                <li
                  key={m.user_id}
                  className="inline-flex items-center gap-1 rounded-md border bg-muted/40 py-0.5 pl-2 pr-1 text-xs"
                >
                  <span className="font-medium">{m.full_name}</span>
                  <span className="text-muted-foreground">{m.email}</span>
                  <button
                    type="button"
                    aria-label={`Remove ${m.full_name} from ${team.name}`}
                    className="rounded-sm p-0.5 text-muted-foreground hover:bg-background hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    disabled={removeMember.isPending}
                    onClick={() =>
                      removeMember.mutate({
                        teamId: team.id,
                        userId: m.user_id,
                      })
                    }
                  >
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="mt-3">
          {showAdd ? (
            <div className="flex flex-wrap items-center gap-2 rounded-md border bg-card p-2">
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger
                  className="h-8 w-[260px]"
                  aria-label={`Select user to add to ${team.name}`}
                >
                  <SelectValue placeholder="Choose a user…" />
                </SelectTrigger>
                <SelectContent>
                  {agentsQuery.isLoading || adminsQuery.isLoading ? (
                    <SelectItem value="__loading" disabled>
                      Loading…
                    </SelectItem>
                  ) : eligible.length === 0 ? (
                    <SelectItem value="__empty" disabled>
                      No eligible users
                    </SelectItem>
                  ) : (
                    eligible.map((u) => (
                      <SelectItem key={u.id} value={u.id}>
                        {u.full_name} · {u.email}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                onClick={onAdd}
                disabled={!selectedUserId || addMember.isPending}
              >
                {addMember.isPending ? "Adding…" : "Add"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setShowAdd(false);
                  setSelectedUserId("");
                }}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAdd(true)}
            >
              <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
              Add member
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Unused but kept to satisfy any older imports elsewhere.
export type { TeamMemberSummary };
