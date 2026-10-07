"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useCreateCategory,
  useDeleteCategory,
} from "@/features/admin/mutations";
import { useAdminCategories } from "@/features/admin/queries";

export default function CategoriesPage() {
  const query = useAdminCategories();
  const create = useCreateCategory();
  const del = useDeleteCategory();

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
          <CardTitle>Add category</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={onSubmit}
            className="grid gap-3 sm:grid-cols-[1fr_2fr_auto] sm:items-end"
          >
            <div className="space-y-1.5">
              <Label htmlFor="cat-name">Name</Label>
              <Input
                id="cat-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cat-desc">Description</Label>
              <Input
                id="cat-desc"
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
        <LoadingState variant="table" rows={5} />
      ) : query.isError ? (
        <ErrorState
          title="Couldn't load categories"
          onRetry={() => query.refetch()}
        />
      ) : query.data ? (
        <Card className="overflow-hidden">
          <table className="w-full text-sm" aria-label="Ticket categories">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th scope="col" className="px-4 py-2.5">
                  Name
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Description
                </th>
                <th scope="col" className="px-4 py-2.5 text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {query.data.items.map((c) => (
                <tr key={c.id}>
                  <td className="px-4 py-3 font-medium">{c.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.description ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Delete category ${c.name}`}
                      onClick={() => {
                        if (window.confirm(`Delete category "${c.name}"?`)) {
                          del.mutate(c.id);
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
