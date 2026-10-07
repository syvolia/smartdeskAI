"""Deterministic mock embedding provider.

Uses a bag-of-words hash to 1536 dimensions, then L2-normalizes. Identical
text produces identical vectors; texts that share tokens produce similar
vectors (cosine similarity > 0). No network calls, no API key.
"""

import hashlib
import math
import time

from app.ai.embeddings.provider import EmbeddingMetadata


def _hash_token(token: str) -> int:
    # hashlib for cross-run determinism (Python's builtin hash is salted).
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class MockEmbeddingProvider:
    name = "mock"

    def __init__(self, *, dimension: int = 1536, model: str = "mock-embed") -> None:
        self.dimension = dimension
        self.model = model

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        tokens = [t for t in text.lower().split() if t]
        if not tokens:
            # Zero vector; downstream code treats this as "no signal".
            return vec

        for token in tokens:
            h = _hash_token(token)
            idx = h % self.dimension
            sign = 1.0 if (h // self.dimension) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [x / norm for x in vec]

    async def embed(
        self,
        texts: list[str],
        *,
        timeout_seconds: float,
    ) -> tuple[list[list[float]], EmbeddingMetadata]:
        started = time.monotonic()
        vectors = [self._embed_one(t) for t in texts]
        latency_ms = int((time.monotonic() - started) * 1000)
        metadata = EmbeddingMetadata(
            provider=self.name,
            model=self.model,
            dimension=self.dimension,
            total_tokens=sum(len(t.split()) for t in texts),
            latency_ms=latency_ms,
        )
        return vectors, metadata