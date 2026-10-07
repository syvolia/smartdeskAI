"""Content cleaning and chunking for the knowledge base.

Splits content into chunks of ~N tokens with a small overlap, preserving
paragraph structure where possible. Token counts are estimated from
character length (1 token ≈ 4 chars for English) — good enough for chunk
sizing, not for billing.
"""

import hashlib
import re

_WS = re.compile(r"[ \t]+")
_NEWLINES = re.compile(r"\n{3,}")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def clean_content(text: str) -> str:
    """Normalize whitespace. Idempotent."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS.sub(" ", text)
    text = _NEWLINES.sub("\n\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    # Cheap approximation. Refined token counting can replace this later.
    return max(1, len(text) // 4)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_long_paragraph(
    paragraph: str, max_chars: int
) -> list[str]:
    """Split an oversized paragraph on sentence boundaries, then hard-wrap."""
    sentences = _SENTENCE_SPLIT.split(paragraph)
    pieces: list[str] = []
    buf = ""
    for sentence in sentences:
        candidate = f"{buf} {sentence}".strip() if buf else sentence
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                pieces.append(buf)
            # A single sentence longer than max_chars → hard wrap.
            while len(sentence) > max_chars:
                pieces.append(sentence[:max_chars])
                sentence = sentence[max_chars:]
            buf = sentence
    if buf:
        pieces.append(buf)
    return pieces


def _apply_overlap(
    chunks: list[str], overlap_chars: int
) -> list[str]:
    """Prepend the tail of the previous chunk to each subsequent chunk."""
    if overlap_chars <= 0 or len(chunks) <= 1:
        return chunks

    out = [chunks[0]]
    for prev, cur in zip(chunks, chunks[1:], strict=False):
        tail = prev[-overlap_chars:] if len(prev) > overlap_chars else prev
        out.append(f"{tail}\n{cur}")
    return out


def chunk_content(
    text: str,
    *,
    target_tokens: int = 400,
    overlap_tokens: int = 60,
) -> list[str]:
    """Split cleaned text into paragraph-aware chunks.

    The size targets are approximate; the actual size depends on where
    paragraph and sentence boundaries fall.
    """
    cleaned = clean_content(text)
    if not cleaned:
        return []

    max_chars = target_tokens * 4
    overlap_chars = overlap_tokens * 4

    # Break into paragraphs, then split oversized ones.
    paragraphs: list[str] = []
    for raw in cleaned.split("\n\n"):
        raw = raw.strip()
        if not raw:
            continue
        if len(raw) <= max_chars:
            paragraphs.append(raw)
        else:
            paragraphs.extend(_split_long_paragraph(raw, max_chars))

    # Merge small paragraphs into chunks of up to max_chars.
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)

    return _apply_overlap(chunks, overlap_chars)