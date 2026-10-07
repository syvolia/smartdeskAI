"""Embedding provider protocol.

Providers accept a batch of strings and return a batch of float vectors
of the configured dimension, plus metadata (tokens, latency).
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmbeddingMetadata:
    provider: str
    model: str
    dimension: int
    total_tokens: int | None
    latency_ms: int


class EmbeddingProvider(Protocol):
    name: str
    dimension: int
    model: str

    async def embed(
        self,
        texts: list[str],
        *,
        timeout_seconds: float,
    ) -> tuple[list[list[float]], EmbeddingMetadata]: ...