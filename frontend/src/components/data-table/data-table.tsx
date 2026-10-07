"use client";

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface DataTableColumn<T> {
  id: string;
  header: string;
  cell: (row: T) => ReactNode;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  className?: string;
  headerClassName?: string;
  hideBelow?: "sm" | "md" | "lg" | "xl";
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  rowHref?: (row: T) => string;
  onRowClick?: (row: T) => void;
  sort?: string;
  order?: "asc" | "desc";
  onSortChange?: (sort: string, order: "asc" | "desc") => void;
  caption?: string;
  ariaLabel?: string;
  loading?: boolean;
  className?: string;
}

const hideBelowClass: Record<
  NonNullable<DataTableColumn<unknown>["hideBelow"]>,
  string
> = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
  xl: "hidden xl:table-cell",
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  rowHref,
  onRowClick,
  sort,
  order,
  onSortChange,
  caption,
  ariaLabel,
  loading,
  className,
}: DataTableProps<T>) {
  const handleSort = (columnId: string) => {
    if (!onSortChange) return;
    if (sort === columnId) {
      onSortChange(columnId, order === "asc" ? "desc" : "asc");
    } else {
      onSortChange(columnId, "desc");
    }
  };

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border border-border bg-card",
        className,
      )}
    >
      <div className="overflow-x-auto">
        <table
          className="w-full text-sm"
          aria-label={ariaLabel}
          aria-busy={loading || undefined}
        >
          {caption ? <caption className="sr-only">{caption}</caption> : null}
          <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              {columns.map((col) => {
                const isSorted = sort === col.id;
                const alignClass =
                  col.align === "right"
                    ? "text-right"
                    : col.align === "center"
                    ? "text-center"
                    : "text-left";
                const hiddenClass = col.hideBelow
                  ? hideBelowClass[col.hideBelow]
                  : "";

                return (
                  <th
                    key={col.id}
                    scope="col"
                    aria-sort={
                      isSorted
                        ? order === "asc"
                          ? "ascending"
                          : "descending"
                        : col.sortable
                        ? "none"
                        : undefined
                    }
                    className={cn(
                      "whitespace-nowrap px-4 py-2.5 font-medium",
                      alignClass,
                      hiddenClass,
                      col.headerClassName,
                    )}
                  >
                    {col.sortable && onSortChange ? (
                      <button
                        type="button"
                        onClick={() => handleSort(col.id)}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                          isSorted && "text-foreground",
                        )}
                      >
                        {col.header}
                        {isSorted ? (
                          order === "asc" ? (
                            <ArrowUp className="h-3 w-3" aria-hidden="true" />
                          ) : (
                            <ArrowDown className="h-3 w-3" aria-hidden="true" />
                          )
                        ) : (
                          <ArrowUpDown
                            className="h-3 w-3 opacity-50"
                            aria-hidden="true"
                          />
                        )}
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((row) => {
              const key = rowKey(row);
              const href = rowHref?.(row);

              return (
                <tr
                  key={key}
                  onClick={
                    onRowClick
                      ? (event) => {
                          if (
                            (event.target as HTMLElement).closest(
                              "a,button,input,select",
                            )
                          ) {
                            return;
                          }
                          onRowClick(row);
                        }
                      : undefined
                  }
                  className={cn(
                    "transition-colors",
                    (onRowClick || href) && "cursor-pointer hover:bg-accent/40",
                  )}
                >
                  {columns.map((col, index) => {
                    const alignClass =
                      col.align === "right"
                        ? "text-right"
                        : col.align === "center"
                        ? "text-center"
                        : "text-left";
                    const hiddenClass = col.hideBelow
                      ? hideBelowClass[col.hideBelow]
                      : "";

                    return (
                      <td
                        key={col.id}
                        className={cn(
                          "px-4 py-3 align-middle",
                          alignClass,
                          hiddenClass,
                          col.className,
                        )}
                      >
                        {href && index === 0 ? (
                          <a
                            href={href}
                            className="block truncate rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                          >
                            {col.cell(row)}
                          </a>
                        ) : (
                          col.cell(row)
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
