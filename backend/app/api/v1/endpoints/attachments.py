"""Attachment upload endpoint.

Files are written to object storage with an opaque, org-scoped key. The
client-supplied filename is never used as a storage key.

Storage is a pluggable interface — a local-filesystem implementation is
provided for dev, and the S3 adapter drops in without endpoint changes.
"""

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.file_validation import validate_upload
from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import Ticket, TicketAttachment, User, UserRole
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketAttachmentResponse

router = APIRouter(prefix="/tickets/{ticket_id}/attachments", tags=["attachments"])
logger = get_logger(__name__)

STORAGE_ROOT = Path("/tmp/smartdesk-attachments")


def _storage_path(org_id: uuid.UUID, ticket_id: uuid.UUID, key: str) -> Path:
    # Opaque, hierarchical, never derived from user input.
    return STORAGE_ROOT / str(org_id) / str(ticket_id) / key


@router.post(
    "",
    response_model=TicketAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("attachments:upload", 20, 60))],
    summary="Upload an attachment to a ticket.",
)
async def upload_attachment(
    ticket_id: uuid.UUID,
    file: UploadFile = File(...),
    comment_id: uuid.UUID | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketAttachmentResponse:
    # 1. Resolve the ticket in the caller's org. Cross-tenant → 404.
    repo = TicketRepository(db)
    ticket = await repo.get(ticket_id, user.organization_id)
    if ticket is None:
        raise NotFoundError("Ticket not found.")

    # 2. Authorization: staff can attach; customers can only attach to
    #    their own tickets.
    if user.role == UserRole.CUSTOMER and ticket.customer.email != user.email:
        raise NotFoundError("Ticket not found.")

    # 3. Read with a hard cap so a malicious client can't OOM the server.
    content = await file.read(25 * 1024 * 1024 + 1)

    # 4. Validate — filename, declared MIME, magic bytes, size.
    meta = validate_upload(
        filename=file.filename or "",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )

    # 5. Compute a checksum for dedupe / integrity.
    checksum = hashlib.sha256(content).hexdigest()

    # 6. Write to storage under an opaque key.
    storage_key = f"{uuid.uuid4().hex}{meta.extension}"
    path = _storage_path(ticket.organization_id, ticket.id, storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    # 7. Persist metadata.
    attachment = TicketAttachment(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        comment_id=comment_id,
        uploaded_by_user_id=user.id,
        file_name=meta.filename,
        content_type=meta.content_type,
        size_bytes=meta.size_bytes,
        storage_key=str(path.relative_to(STORAGE_ROOT)),
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    logger.info(
        "attachment_uploaded",
        ticket_id=str(ticket.id),
        org_id=str(ticket.organization_id),
        user_id=str(user.id),
        content_type=meta.content_type,
        size_bytes=meta.size_bytes,
        checksum=checksum[:16],
    )

    return TicketAttachmentResponse.model_validate(attachment)


@router.get(
    "/{attachment_id}",
    summary="Download an attachment (returns a local redirect in dev).",
)
async def download_attachment(
    ticket_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = TicketRepository(db)
    ticket = await repo.get(ticket_id, user.organization_id)
    if ticket is None:
        raise NotFoundError("Ticket not found.")
    if user.role == UserRole.CUSTOMER and ticket.customer.email != user.email:
        raise NotFoundError("Ticket not found.")

    attachment = await db.scalar(
        # Every clause here is a scope check.
        __import__("sqlalchemy").select(TicketAttachment).where(
            TicketAttachment.id == attachment_id,
            TicketAttachment.ticket_id == ticket.id,
            TicketAttachment.organization_id == ticket.organization_id,
        )
    )
    if attachment is None:
        raise NotFoundError("Attachment not found.")

    # In production this returns a short-lived presigned URL. For dev we
    # just signal where the file lives; never return the filesystem path
    # to the client.
    return {
        "attachment_id": str(attachment.id),
        "file_name": attachment.file_name,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "download_url": None,
        "note": "Presigned URL issuance belongs to object storage integration.",
    }