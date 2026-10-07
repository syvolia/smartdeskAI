import { Badge } from "@/components/ui/badge";
import type { CustomerSentiment } from "@/types/ai";

const LABELS: Record<CustomerSentiment, string> = {
  positive: "Positive",
  neutral: "Neutral",
  frustrated: "Frustrated",
  angry: "Angry",
};

export function SentimentBadge({ value }: { value: CustomerSentiment }) {
  const variant =
    value === "positive"
      ? "success"
      : value === "frustrated"
      ? "warning"
      : value === "angry"
      ? "danger"
      : "neutral";
  return <Badge variant={variant}>Customer: {LABELS[value]}</Badge>;
}
