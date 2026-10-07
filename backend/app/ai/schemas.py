"""Structured output schemas for AI operations.

Every AI response is validated against one of these models before it is
persisted. This is what "structured outputs" means in this codebase:
the provider is contractually required to return JSON matching the
schema, and Pydantic enforces it on the way in.

Order matters: enums are declared before the models that reference them.
Python evaluates class bodies at import time, so a default value like
`ResponseTone.FRIENDLY` cannot appear above `class ResponseTone`.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import TicketPriority

from uuid import UUID

# ---------- shared types (must come before classes that default them) ----------


class ResponseTone(str, Enum):
    FORMAL = "formal"
    FRIENDLY = "friendly"
    CONCISE = "concise"


class NextAction(str, Enum):
    REQUEST_INFORMATION = "request_information"
    PROVIDE_SOLUTION = "provide_solution"
    ESCALATE = "escalate"
    ASSIGN_SPECIALIST = "assign_specialist"
    RESOLVE = "resolve"


CustomerSentiment = Literal["positive", "neutral", "frustrated", "angry"]


# ---------- per-operation output models ----------


class ClassificationResult(BaseModel):
    """Categorization of a ticket into one of the org's categories."""

    category_name: str = Field(
        description=(
            "Exact name of one of the provided categories, or 'General' "
            "if none apply."
        ),
        max_length=100,
    )
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str = Field(max_length=500)


class PriorityResult(BaseModel):
    """Suggested priority for a ticket."""

    suggested_priority: TicketPriority
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str = Field(max_length=500)


class SummaryResult(BaseModel):
    """Concise agent-facing summary of a ticket conversation."""

    summary: str = Field(max_length=2000)
    key_points: list[str] = Field(min_length=1, max_length=8)
    customer_sentiment: CustomerSentiment = "neutral"


class SuggestedResponseResult(BaseModel):
    """Draft reply for the agent to review and send."""

    draft: str = Field(max_length=4000)
    tone: ResponseTone = ResponseTone.FRIENDLY
    cited_article_ids: list[str] = Field(default_factory=list, max_length=5)


class NextActionResult(BaseModel):
    """Recommended next step for the agent handling the ticket."""

    action: NextAction
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str = Field(max_length=500)

    # ---------- RAG ----------


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class KnowledgeChunkMatch(BaseModel):
    chunk_id: UUID
    article_id: UUID
    article_title: str
    article_slug: str
    chunk_index: int
    content: str
    similarity: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeChunkMatch]
    total: int
    min_similarity_used: float


class KnowledgeAskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class KnowledgeCitation(BaseModel):
    source_number: int
    article_id: UUID
    article_title: str
    article_slug: str
    chunk_id: UUID
    excerpt: str


class KnowledgeAskResponse(BaseModel):
    query: str
    answer: str
    is_grounded: bool
    confidence: float | None
    citations: list[KnowledgeCitation]
    used_chunks: int
    no_evidence_reason: str | None = None


class RAGAnswer(BaseModel):
    """LLM output for the /ask endpoint. Validated before returning."""

    answer: str = Field(max_length=4000)
    cited_source_numbers: list[int] = Field(default_factory=list, max_length=10)
    is_grounded: bool
    confidence: float = Field(ge=0.0, le=1.0)