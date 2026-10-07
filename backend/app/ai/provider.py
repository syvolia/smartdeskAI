"""LLM provider protocol and metadata type.

A provider is a thin adapter over an LLM API. It must accept a Pydantic
schema, request structured output, and return a validated instance of
that schema. Anything else (timeouts, auth, retries) is the provider's
responsibility, surfaced through the AI exception hierarchy.
"""

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class LLMMetadata:
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


class LLMProvider(Protocol):
    name: str

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: type[SchemaT],
        timeout_seconds: float,
    ) -> tuple[SchemaT, LLMMetadata]: ...