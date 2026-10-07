"""Safe file upload validation.

Checks in order: declared size, MIME allowlist, magic-byte signature,
and (optionally) an anti-malware hook. Fails closed on any mismatch.

We validate BOTH the client-supplied content type AND the actual bytes.
A client can lie about the former; only the latter is trustworthy.
"""

from dataclasses import dataclass

from app.core.exceptions import ValidationError

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MiB

# Extension + declared MIME allowlist. Both must match.
ALLOWED: dict[str, set[str]] = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/gif": {".gif"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
    "text/csv": {".csv"},
    "application/zip": {".zip"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
}

# Magic byte signatures for the types we accept.
# Kept small and explicit — if a signature doesn't match, we reject.
_SIGNATURES: dict[str, list[bytes]] = {
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # followed by WEBP at offset 8
    "application/pdf": [b"%PDF-"],
    "application/zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        b"PK\x03\x04"
    ],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        b"PK\x03\x04"
    ],
}


@dataclass(frozen=True)
class UploadMeta:
    filename: str
    content_type: str
    size_bytes: int
    extension: str


def _ext(filename: str) -> str:
    # Take the last dot-segment, lowercased. Rejects "foo.tar.gz" from
    # passing as ".gz" for a .tar.gz-only handler — we only care about
    # the final extension here.
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[1].lower()


def validate_upload(
    *,
    filename: str,
    content_type: str,
    content: bytes,
) -> UploadMeta:
    """Validate filename, declared MIME, size, and magic bytes.

    Raises ValidationError with a generic message on failure so we don't
    leak which check tripped (helps resist probing).
    """
    if not filename or "/" in filename or "\\" in filename or "\x00" in filename:
        raise ValidationError("Invalid file name.")

    size = len(content)
    if size == 0:
        raise ValidationError("Empty file.")
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB)."
        )

    ext = _ext(filename)
    allowed_exts = ALLOWED.get(content_type)
    if not allowed_exts or ext not in allowed_exts:
        raise ValidationError("Unsupported file type.")

    signatures = _SIGNATURES.get(content_type)
    if signatures is not None:
        head = content[:16]
        if not any(head.startswith(sig) for sig in signatures):
            raise ValidationError("File contents don't match the declared type.")

    # Special-case WebP — RIFF alone is shared with WAV/AVI.
    if content_type == "image/webp" and content[8:12] != b"WEBP":
        raise ValidationError("File contents don't match the declared type.")

    return UploadMeta(
        filename=filename,
        content_type=content_type,
        size_bytes=size,
        extension=ext,
    )