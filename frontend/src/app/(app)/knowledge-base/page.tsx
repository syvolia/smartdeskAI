import type { Metadata } from "next";
import { BookOpen } from "lucide-react";

import { PlaceholderPage } from "@/components/layout/placeholder-page";

export const metadata: Metadata = { title: "Knowledge base" };

export default function KnowledgeBasePage() {
  return (
    <PlaceholderPage
      title="Knowledge base"
      description="Write, publish, and search the articles your team uses every day."
      icon={BookOpen}
      emptyTitle="Knowledge base coming next"
      emptyDescription="Categories, articles, and full-text search land here in a later phase."
    />
  );
}
