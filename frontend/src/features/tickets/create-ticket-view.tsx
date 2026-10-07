"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Send } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { apiClient, apiV1, ApiError } from "@/lib/api-client";
import { ticketKeys } from "@/features/tickets/queries";
import { PRIORITY_OPTIONS } from "@/features/tickets/ticket-options";
import type { Ticket, TicketListResponse } from "@/types/ticket";

interface CustomerOption {
  id: string;
  full_name: string;
  email: string;
}

export function CreateTicketView() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [customerId, setCustomerId] = useState<string>("");
  const [priority, setPriority] = useState<string>("MEDIUM");
  const [source, setSource] = useState<string>("WEB");

  // Reuse the ticket list query to derive a small customer picker. This
  // is fine while the customer directory endpoint doesn't exist yet.
  const customersQuery = useQuery({
    queryKey: ["tickets", "recent-customers"],
    queryFn: () =>
      apiClient.get<TicketListResponse>(apiV1("/tickets"), {
        query: { page: 1, page_size: 100, sort: "updated_at", order: "desc" },
      }),
  });

  const customers: CustomerOption[] = (() => {
    const map = new Map<string, CustomerOption>();
    for (const t of customersQuery.data?.items ?? []) {
      if (!map.has(t.customer.id)) {
        map.set(t.customer.id, {
          id: t.customer.id,
          full_name: t.customer.full_name,
          email: t.customer.email,
        });
      }
    }
    return Array.from(map.values()).sort((a, b) =>
      a.full_name.localeCompare(b.full_name),
    );
  })();

  const createMutation = useMutation<Ticket, ApiError, void>({
    mutationFn: () =>
      apiClient.post<Ticket>(apiV1("/tickets"), {
        title: title.trim(),
        description: description.trim(),
        customer_id: customerId,
        priority,
        source,
      }),
    onSuccess: (ticket) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() });
      toast({
        title: "Ticket created",
        description: "You can now assign and reply.",
        variant: "success",
      });
      router.replace(`/tickets/${ticket.id}`);
    },
    onError: (error) => {
      toast({
        title: "Couldn't create ticket",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim() || !customerId) {
      toast({
        title: "Fill in all required fields",
        variant: "destructive",
      });
      return;
    }
    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2">
          <Link href="/tickets">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to tickets
          </Link>
        </Button>
        <PageHeader
          title="New ticket"
          description="Log a customer request. You can assign, categorize, and reply once it's created."
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ticket details</CardTitle>
          <CardDescription>
            Title and description are shown to agents and (if the reply is
            public) to the customer.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-5 max-w-2xl">
            <div className="space-y-1.5">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Short summary of the issue"
                required
                maxLength={500}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is the customer asking for? Include steps to reproduce if relevant."
                rows={6}
                required
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1.5 sm:col-span-1">
                <Label htmlFor="customer">Customer</Label>
                <Select value={customerId} onValueChange={setCustomerId}>
                  <SelectTrigger id="customer" aria-label="Customer">
                    <SelectValue placeholder="Select a customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customersQuery.isLoading ? (
                      <SelectItem value="__loading" disabled>
                        Loading…
                      </SelectItem>
                    ) : customers.length === 0 ? (
                      <SelectItem value="__empty" disabled>
                        No customers yet
                      </SelectItem>
                    ) : (
                      customers.map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.full_name}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="priority">Priority</Label>
                <Select value={priority} onValueChange={setPriority}>
                  <SelectTrigger id="priority" aria-label="Priority">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITY_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="source">Source</Label>
                <Select value={source} onValueChange={setSource}>
                  <SelectTrigger id="source" aria-label="Source">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="WEB">Web</SelectItem>
                    <SelectItem value="EMAIL">Email</SelectItem>
                    <SelectItem value="CHAT">Chat</SelectItem>
                    <SelectItem value="PHONE">Phone</SelectItem>
                    <SelectItem value="API">API</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => router.push("/tickets")}
                disabled={createMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || !customerId}
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2
                      className="h-4 w-4 animate-spin"
                      aria-hidden="true"
                    />
                    Creating…
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" aria-hidden="true" />
                    Create ticket
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
