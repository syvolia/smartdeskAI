"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  AIConfidenceBucket,
  NameValue,
  TimeSeriesPoint,
} from "@/types/analytics";
import { formatDuration } from "@/lib/format";

const PRIORITY_COLORS: Record<string, string> = {
  LOW: "#94a3b8",
  MEDIUM: "#3b82f6",
  HIGH: "#f59e0b",
  URGENT: "#ef4444",
};

const STATUS_COLORS: Record<string, string> = {
  OPEN: "#3b82f6",
  IN_PROGRESS: "#0ea5e9",
  WAITING_CUSTOMER: "#f59e0b",
  RESOLVED: "#10b981",
  CLOSED: "#6b7280",
};

const CATEGORY_PALETTE = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#ec4899",
];

function ChartWrapper({
  title,
  description,
  height = 280,
  children,
}: {
  title: string;
  description?: string;
  height?: number;
  children: React.ReactNode;
}) {
  return (
    <div className="w-full">
      <div className="mb-2">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {description ? (
          <p className="text-xs text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div
        role="img"
        aria-label={title}
        style={{ width: "100%", height }}
        className="text-xs"
      >
        <ResponsiveContainer width="100%" height="100%">
          {children as React.ReactElement}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ---------- ticket volume ----------

export function TicketVolumeChart({
  created,
  resolved,
}: {
  created: TimeSeriesPoint[];
  resolved: TimeSeriesPoint[];
}) {
  // Merge on bucket.
  const map = new Map<
    string,
    { bucket: string; created: number; resolved: number }
  >();
  for (const p of created) {
    map.set(p.bucket, { bucket: p.bucket, created: p.count, resolved: 0 });
  }
  for (const p of resolved) {
    const existing = map.get(p.bucket);
    if (existing) {
      existing.resolved = p.count;
    } else {
      map.set(p.bucket, { bucket: p.bucket, created: 0, resolved: p.count });
    }
  }
  const data = Array.from(map.values()).sort((a, b) =>
    a.bucket.localeCompare(b.bucket),
  );

  return (
    <ChartWrapper
      title="Ticket volume"
      description="Created vs. resolved over the selected period."
      height={300}
    >
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="bucket"
          tickFormatter={(v) => v.slice(5, 10)}
          stroke="#6b7280"
        />
        <YAxis stroke="#6b7280" allowDecimals={false} />
        <Tooltip
          contentStyle={{ fontSize: 12 }}
          labelFormatter={(v) => `Date: ${v.slice(0, 10)}`}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="created"
          stroke="#3b82f6"
          strokeWidth={2}
          name="Created"
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="resolved"
          stroke="#10b981"
          strokeWidth={2}
          name="Resolved"
          dot={false}
        />
      </LineChart>
    </ChartWrapper>
  );
}

// ---------- status distribution ----------

export function TicketStatusChart({ data }: { data: NameValue[] }) {
  return (
    <ChartWrapper title="Tickets by status" height={280}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 16, bottom: 8, left: 24 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="#e5e7eb"
          horizontal={false}
        />
        <XAxis type="number" stroke="#6b7280" allowDecimals={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          stroke="#6b7280"
          tickFormatter={(v) => String(v).replace(/_/g, " ")}
        />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={STATUS_COLORS[entry.name] ?? "#6b7280"}
            />
          ))}
        </Bar>
      </BarChart>
    </ChartWrapper>
  );
}

// ---------- priority distribution ----------

export function PriorityDistributionChart({ data }: { data: NameValue[] }) {
  return (
    <ChartWrapper title="Priority distribution" height={280}>
      <PieChart>
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={45}
          outerRadius={90}
          paddingAngle={2}
        >
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={PRIORITY_COLORS[entry.name] ?? "#6b7280"}
            />
          ))}
        </Pie>
      </PieChart>
    </ChartWrapper>
  );
}

// ---------- category distribution ----------

export function CategoryDistributionChart({ data }: { data: NameValue[] }) {
  const top = data.slice(0, 8);
  return (
    <ChartWrapper title="Tickets by category" height={300}>
      <BarChart data={top} margin={{ top: 8, right: 16, bottom: 40, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="name"
          stroke="#6b7280"
          tick={{ fontSize: 10 }}
          interval={0}
          angle={-20}
          textAnchor="end"
          height={50}
        />
        <YAxis stroke="#6b7280" allowDecimals={false} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {top.map((entry, i) => (
            <Cell
              key={entry.name}
              fill={CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]}
            />
          ))}
        </Bar>
      </BarChart>
    </ChartWrapper>
  );
}

// ---------- SLA card content (not a chart) ----------

export function SLAStatsRow({
  firstResponseAvgSeconds,
  resolutionAvgSeconds,
  compliance,
}: {
  firstResponseAvgSeconds: number | null;
  resolutionAvgSeconds: number | null;
  compliance: number;
}) {
  return (
    <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div>
        <dt className="text-xs uppercase tracking-wide text-muted-foreground">
          Avg. first response
        </dt>
        <dd className="mt-1 text-lg font-semibold tabular-nums">
          {formatDuration(firstResponseAvgSeconds)}
        </dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-muted-foreground">
          Avg. resolution time
        </dt>
        <dd className="mt-1 text-lg font-semibold tabular-nums">
          {formatDuration(resolutionAvgSeconds)}
        </dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-muted-foreground">
          SLA compliance
        </dt>
        <dd className="mt-1 text-lg font-semibold tabular-nums">
          {compliance.toFixed(1)}%
        </dd>
      </div>
    </dl>
  );
}

// ---------- agent workload ----------

export function AgentWorkloadChart({
  rows,
}: {
  rows: {
    agent_name: string;
    open_tickets: number;
    in_progress_tickets: number;
    waiting_customer_tickets: number;
    resolved_tickets: number;
    closed_tickets: number;
  }[];
}) {
  return (
    <ChartWrapper title="Agent workload" height={320}>
      <BarChart
        data={rows}
        margin={{ top: 8, right: 16, bottom: 40, left: 0 }}
        stackOffset="none"
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="agent_name"
          stroke="#6b7280"
          tick={{ fontSize: 11 }}
          interval={0}
        />
        <YAxis stroke="#6b7280" allowDecimals={false} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="open_tickets" stackId="a" fill="#3b82f6" name="Open" />
        <Bar
          dataKey="in_progress_tickets"
          stackId="a"
          fill="#0ea5e9"
          name="In progress"
        />
        <Bar
          dataKey="waiting_customer_tickets"
          stackId="a"
          fill="#f59e0b"
          name="Waiting"
        />
        <Bar
          dataKey="resolved_tickets"
          stackId="a"
          fill="#10b981"
          name="Resolved"
        />
        <Bar
          dataKey="closed_tickets"
          stackId="a"
          fill="#6b7280"
          name="Closed"
        />
      </BarChart>
    </ChartWrapper>
  );
}

// ---------- AI confidence ----------

export function AIConfidenceChart({
  buckets,
}: {
  buckets: AIConfidenceBucket[];
}) {
  return (
    <ChartWrapper
      title="AI classification confidence"
      description="Distribution of confidence scores on AI suggestions."
      height={280}
    >
      <BarChart
        data={buckets}
        margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="bucket" stroke="#6b7280" />
        <YAxis stroke="#6b7280" allowDecimals={false} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Bar
          dataKey="count"
          fill="#8b5cf6"
          radius={[4, 4, 0, 0]}
          name="Suggestions"
        />
      </BarChart>
    </ChartWrapper>
  );
}
