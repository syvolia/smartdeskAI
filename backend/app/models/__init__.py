"""ORM models package.

Importing this package registers every model with SQLAlchemy's metadata,
which is required both for Alembic autogenerate and for
`Base.metadata.create_all` in tests.
"""

from app.models.ai import AIJob, AISuggestion
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import (
    AIJobStatus,
    AIOperation,
    AISuggestionKind,
    AISuggestionStatus,
    ArticleStatus,
    NotificationType,
    TicketEventType,
    TicketPriority,
    TicketSource,
    TicketStatus,
    UserRole,
)
from app.models.knowledge_base import (
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
)
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.sla import SLA
from app.models.notification_preference import NotificationPreference
from app.models.team import Team, TeamMember
from app.models.ticket import (
    Ticket,
    TicketAssignment,
    TicketAttachment,
    TicketCategory,
    TicketComment,
)
from app.models.ticket_event import TicketEvent
from app.models.user import User

__all__ = [
    "AIJob",
    "AIJobStatus",
    "AIOperation",
    "AISuggestion",
    "AISuggestionKind",
    "AISuggestionStatus",
    "ArticleStatus",
    "AuditLog",
    "Customer",
    "KnowledgeBaseArticle",
    "KnowledgeBaseCategory",
    "KnowledgeChunk",
    "Notification",
    "NotificationType",
    "Organization",
    "RefreshToken",
    "SLA",
    "Team",
    "TeamMember",
    "Ticket",
    "TicketAssignment",
    "TicketAttachment",
    "TicketCategory",
    "TicketComment",
    "TicketEvent",
    "TicketEventType",
    "TicketPriority",
    "TicketSource",
    "TicketStatus",
    "User",
    "UserRole",
    "NotificationPreference",
]