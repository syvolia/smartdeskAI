"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment, useMemo } from "react";

import { navLabelForPath } from "@/lib/nav";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function humanizeSegment(segment: string): string {
  if (UUID_RE.test(segment)) return "Details";
  return segment
    .split("-")
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join(" ");
}

export function Breadcrumbs() {
  const pathname = usePathname();

  const crumbs = useMemo(() => {
    const parts = pathname.split("/").filter(Boolean);
    return parts.map((segment, index) => {
      const href = `/${parts.slice(0, index + 1).join("/")}`;
      const isLast = index === parts.length - 1;
      const topLevelLabel = index === 0 ? navLabelForPath(href) : null;
      return {
        href,
        label: topLevelLabel ?? humanizeSegment(segment),
        isLast,
      };
    });
  }, [pathname]);

  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <li>
          <Link
            href="/dashboard"
            className="rounded transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            Home
          </Link>
        </li>
        {crumbs.map((crumb) => (
          <Fragment key={crumb.href}>
            <ChevronRight
              className="h-3.5 w-3.5 shrink-0 opacity-60"
              aria-hidden="true"
            />
            <li className="min-w-0">
              {crumb.isLast ? (
                <span
                  aria-current="page"
                  className="block truncate font-medium text-foreground"
                >
                  {crumb.label}
                </span>
              ) : (
                <Link
                  href={crumb.href}
                  className="block truncate rounded transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  {crumb.label}
                </Link>
              )}
            </li>
          </Fragment>
        ))}
      </ol>
    </nav>
  );
}
