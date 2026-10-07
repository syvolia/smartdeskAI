"use client";

import { Mail, Phone, Search, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DataTablePagination } from "@/components/data-table/pagination";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCustomers } from "@/features/customers/queries";
import { formatRelativeTime } from "@/lib/utils";

export function CustomersView() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const query = useCustomers({
    search: search || undefined,
    page,
    page_size: pageSize,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customers"
        description="Everyone who raises tickets with your team."
      />

      <div className="relative max-w-md">
        <Search
          className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          type="search"
          placeholder="Search by name, email, or company…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="pl-8"
          aria-label="Search customers"
        />
      </div>

      {query.isLoading && !query.data ? (
        <LoadingState variant="table" rows={8} />
      ) : query.isError ? (
        <ErrorState
          title="Couldn't load customers"
          description="The customer service didn't respond. Try again in a moment."
          onRetry={() => query.refetch()}
        />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState
          icon={Users}
          title={search ? "No matching customers" : "No customers yet"}
          description={
            search
              ? "Try a different search term."
              : "Customers will appear here when tickets are created for them."
          }
        />
      ) : query.data ? (
        <div className="space-y-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" aria-label="Customers">
                <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 font-medium">
                      Name
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-medium">
                      Email
                    </th>
                    <th
                      scope="col"
                      className="hidden px-4 py-2.5 font-medium md:table-cell"
                    >
                      Company
                    </th>
                    <th
                      scope="col"
                      className="hidden px-4 py-2.5 font-medium lg:table-cell"
                    >
                      Phone
                    </th>
                    <th
                      scope="col"
                      className="hidden px-4 py-2.5 font-medium sm:table-cell"
                    >
                      Added
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {query.data.items.map((c) => (
                    <tr
                      key={c.id}
                      className="transition-colors hover:bg-accent/40"
                    >
                      <td className="px-4 py-3 font-medium">
                        <Link
                          href={`/tickets?customer_id=${c.id}`}
                          className="rounded hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        >
                          {c.full_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        <span className="inline-flex items-center gap-1.5">
                          <Mail
                            className="h-3.5 w-3.5 opacity-60"
                            aria-hidden="true"
                          />
                          {c.email}
                        </span>
                      </td>
                      <td className="hidden px-4 py-3 md:table-cell">
                        {c.company ? (
                          <Badge variant="neutral">{c.company}</Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="hidden px-4 py-3 text-muted-foreground lg:table-cell">
                        {c.phone ? (
                          <span className="inline-flex items-center gap-1.5">
                            <Phone
                              className="h-3.5 w-3.5 opacity-60"
                              aria-hidden="true"
                            />
                            {c.phone}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="hidden whitespace-nowrap px-4 py-3 text-muted-foreground sm:table-cell">
                        {formatRelativeTime(c.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <DataTablePagination
            page={query.data.page}
            pageSize={query.data.page_size}
            total={query.data.total}
            pages={query.data.pages}
            onPageChange={setPage}
            disabled={query.isFetching}
          />
        </div>
      ) : null}
    </div>
  );
}
