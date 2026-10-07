"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

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
import { useCreateSLA, useDeleteSLA } from "@/features/admin/mutations";
import { useAdminSlas } from "@/features/admin/queries";

export default function SLAsPage() {
  const query = useAdminSlas();
  const create = useCreateSLA();
  const del = useDeleteSLA();

  const [name, setName] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [firstResponse, setFirstResponse] = useState("60");
  const [resolution, setResolution] = useState("480");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(
      {
        name,
        priority,
        first_response_minutes: parseInt(firstResponse, 10),
        resolution_minutes: parseInt(resolution, 10),
        is_active: true,
      },
      {
        onSuccess: () => {
          setName("");
          setPriority("MEDIUM");
          setFirstResponse("60");
          setResolution("480");
        },
      },
    );
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Add SLA policy</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={onSubmit}
            className="grid gap-3 sm:grid-cols-5 sm:items-end"
          >
            <div className="space-y-1.5">
              <Label htmlFor="sla-name">Name</Label>
              <Input
                id="sla-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sla-priority">Priority</Label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger id="sla-priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LOW">Low</SelectItem>
                  <SelectItem value="MEDIUM">Medium</SelectItem>
                  <SelectItem value="HIGH">High</SelectItem>
                  <SelectItem value="URGENT">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sla-fr">First response (min)</Label>
              <Input
                id="sla-fr"
                type="number"
                min={1}
                value={firstResponse}
                onChange={(e) => setFirstResponse(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sla-res">Resolution (min)</Label>
              <Input
                id="sla-res"
                type="number"
                min={1}
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                required
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
        <LoadingState variant="table" rows={4} />
      ) : query.isError ? (
        <ErrorState
          title="Couldn't load SLAs"
          onRetry={() => query.refetch()}
        />
      ) : query.data ? (
        <Card className="overflow-hidden">
          <table className="w-full text-sm" aria-label="SLA policies">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th scope="col" className="px-4 py-2.5">
                  Name
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Priority
                </th>
                <th scope="col" className="px-4 py-2.5">
                  First response
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Resolution
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Status
                </th>
                <th scope="col" className="px-4 py-2.5 text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {query.data.items.map((s: any) => (
                <tr key={s.id}>
                  <td className="px-4 py-3 font-medium">{s.name}</td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{s.priority}</Badge>
                  </td>
                  <td className="px-4 py-3">{s.first_response_minutes} min</td>
                  <td className="px-4 py-3">{s.resolution_minutes} min</td>
                  <td className="px-4 py-3">
                    <Badge variant={s.is_active ? "success" : "neutral"}>
                      {s.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Delete SLA ${s.name}`}
                      onClick={() => {
                        if (window.confirm(`Delete SLA "${s.name}"?`)) {
                          del.mutate(s.id);
                        }
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  );
}
