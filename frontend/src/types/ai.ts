import type { TicketPriority } from "@/types/ticket";

export type AIOperation =
  | "CLASSIFY"
  | "SUGGEST_PRIORITY"
  | "SUMMARIZE"
  | "SUGGEST_RESPONSE"
  | "SUGGEST_NEXT_ACTION";

export type AISuggestionKind =
  | "CLASSIFICATION"
  | "PRIORITY"
  | "SUMMARY"
  | "SUGGESTED_RESPONSE"
  | "NEXT_ACTION";

export type AISuggestionStatus =
  | "PENDING"
  | "ACCEPTED"
  | "REJECTED"
  | "SUPERSEDED";

export interface AISuggestion {
  id: string;
  organization_id: string;
  ticket_id: string;
  kind: AISuggestionKind;
  status: AISuggestionStatus;
  payload: Record<string, unknown>;
  confidence: number | null;
  model: string;
  created_at: string;
  updated_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
}

export interface AISuggestionListResponse {
  items: AISuggestion[];
  total: number;
}

export interface AIAcceptResponse {
  suggestion: AISuggestion;
}

// ---- payload shapes (mirror backend/app/ai/schemas.py) ----

export interface ClassificationPayload {
  category_name: string;
  category_id: string | null;
  confidence: number;
  reasoning_summary: string;
}

export interface PriorityPayload {
  suggested_priority: TicketPriority;
  confidence: number;
  reasoning_summary: string;
}

export type CustomerSentiment = "positive" | "neutral" | "frustrated" | "angry";

export interface SummaryPayload {
  summary: string;
  key_points: string[];
  customer_sentiment: CustomerSentiment;
}

export type ResponseTone = "formal" | "friendly" | "concise";

export interface CitedArticle {
  id: string;
  title: string;
  excerpt: string;
}

export interface SuggestedResponsePayload {
  draft: string;
  tone: ResponseTone;
  cited_article_ids: string[];
  cited_articles?: CitedArticle[];
}

export type NextAction =
  | "request_information"
  | "provide_solution"
  | "escalate"
  | "assign_specialist"
  | "resolve";

export interface NextActionPayload {
  action: NextAction;
  confidence: number;
  reasoning_summary: string;
}

// ---- helpers ----

export function asClassificationPayload(
  payload: Record<string, unknown>
): ClassificationPayload {
  return payload as unknown as ClassificationPayload;
}
export function asPriorityPayload(
  payload: Record<string, unknown>
): PriorityPayload {
  return payload as unknown as PriorityPayload;
}
export function asSummaryPayload(
  payload: Record<string, unknown>
): SummaryPayload {
  return payload as unknown as SummaryPayload;
}
export function asSuggestedResponsePayload(
  payload: Record<string, unknown>
): SuggestedResponsePayload {
  return payload as unknown as SuggestedResponsePayload;
}
export function asNextActionPayload(
  payload: Record<string, unknown>
): NextActionPayload {
  return payload as unknown as NextActionPayload;
}