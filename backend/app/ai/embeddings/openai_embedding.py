"""OpenAI-backed embedding provider."""

import asyncio
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)

from app.ai.embeddings.provider import EmbeddingMetadata


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimension: int,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, max_retries=1)
        self.model = model
        self.dimension = dimension

    async def embed(
        self,
        texts: list[str],
        *,
        timeout_seconds: float,
    ) -> tuple[list[list[float]], EmbeddingMetadata]:
        from app.ai.exceptions import AITimeoutError, AIUnavailableError

        if not texts:
            return [], EmbeddingMetadata(
                provider=self.name,
                model=self.model,
                dimension=self.dimension,
                total_tokens=0,
                latency_ms=0,
            )

        started = time.monotonic()
        try:
            response = await asyncio.wait_for(
                self._client.embeddings.create(
                    model=self.model,
                    input=texts,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise AITimeoutError() from exc
        except APITimeoutError as exc:
            raise AITimeoutError() from exc
        except (APIConnectionError, APIStatusError) as exc:
            raise AIUnavailableError() from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        vectors = [list(d.embedding) for d in response.data]

        if any(len(v) != self.dimension for v in vectors):
            from app.ai.exceptions import AIInvalidResponseError

            raise AIInvalidResponseError(
                f"Embedding dimension mismatch (expected {self.dimension})"
            )

        metadata = EmbeddingMetadata(
            provider=self.name,
            model=self.model,
            dimension=self.dimension,
            total_tokens=getattr(response.usage, "total_tokens", None)
            if getattr(response, "usage", None)
            else None,
            latency_ms=latency_ms,
        )
        return vectors, metadata