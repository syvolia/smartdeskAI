export interface NameValue {
  name: string;
  value: number;
}

export interface TimeSeriesPoint {
  bucket: string;
  count: number;
}

export interface TicketOverview {
  total: number;
  open: number;
  in_progress: number;
  waiting_customer: number;
  resolved: number;
  closed: number;
  by_priority: NameValue[];
  by_status: NameValue[];
  by_category: NameValue[];
}

export interface TicketTimeSeries {
  created: TimeSeriesPoint[];
  resolved: TimeSeriesPoint[];
}

export interface SLAMetrics {
  first_response_avg_seconds: number | null;
  first_response_samples: number;
  resolution_avg_seconds: number | null;
  resolution_samples: number;
  sla_compliance_percentage: number;
  breached: number;
  total_with_sla: number;
}

export interface AgentWorkloadRow {
  agent_id: string | null;
  agent_name: string;
  open_tickets: number;
  in_progress_tickets: number;
  waiting_customer_tickets: number;
  resolved_tickets: number;
  closed_tickets: number;
  total_assigned: number;
}

export interface AIOverallMetrics {
  suggestions_generated: number;
  suggestions_accepted: number;
  suggestions_rejected: number;
  suggestions_pending: number;
  acceptance_rate: number;
  assisted_tickets: number;
}

export interface AIByKindRow {
  kind: string;
  generated: number;
  accepted: number;
  rejected: number;
  acceptance_rate: number;
}

export interface AIConfidenceBucket {
  bucket: string;
  min: number;
  max: number;
  count: number;
}

export interface AIAnalytics {
  overall: AIOverallMetrics;
  by_kind: AIByKindRow[];
  confidence_distribution: AIConfidenceBucket[];
}

export interface AnalyticsDashboard {
  date_from: string;
  date_to: string;
  tickets: TicketOverview;
  time_series: TicketTimeSeries;
  sla: SLAMetrics;
  agents: AgentWorkloadRow[];
  ai: AIAnalytics;
}