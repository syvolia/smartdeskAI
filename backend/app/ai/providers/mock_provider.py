"""Deterministic mock provider for tests and local development.

Callers register one response per schema type; anything not registered
falls back to a generic default built by introspecting the schema.

Design notes:
- `_build_default` must produce values that satisfy every Pydantic
  constraint on the schema, including `min_length` on list fields. That's
  why list fields get one item rather than an empty list.
- Enum fields default to their first declared value.
- Nested Pydantic models are built recursively.
- `Optional[...]` fields resolve to None.
"""

import asyncio
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from app.ai.provider import LLMMetadata, SchemaT


def _sample_for(annotation: Any, field_name: str) -> Any:
    """Best-effort sample value for a Pydantic field annotation."""
    origin = getattr(annotation, "__origin__", None)
    type_name = getattr(annotation, "__name__", "")

    # Primitives
    if annotation is str:
        return f"mock-{field_name}"
    if annotation is int:
        return 1
    if annotation is float:
        return 0.5
    if annotation is bool:
        return False
    if annotation is type(None):
        return None

    # Containers
    if origin is list or type_name == "list":
        # Return one element so min_length=1 constraints are satisfied.
        args = getattr(annotation, "__args__", ())
        inner = args[0] if args else str
        return [_sample_for(inner, f"{field_name}-1")]

    if origin is dict:
        return {}

    # Enums
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return list(annotation)[0]

    # Nested models
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _build_default(annotation)

    # Fallback for anything we don't recognize (e.g. Union, Literal).
    # Returning None is safe for Optional[...] fields, which are the
    # common case here.
    return None


def _build_default(schema: type[BaseModel]) -> BaseModel:
    """Build a valid instance of `schema` with placeholder values.

    Fields with defaults are left alone. Fields without defaults get a
    value from `_sample_for`. Fields annotated as `Optional[...]` (or with
    `X | None`) will resolve to None via the fallback branch.
    """
    kwargs: dict[str, Any] = {}
    for name, field in schema.model_fields.items():
        if field.default is not PydanticUndefined:
            continue
        # Skip optional fields so the model uses its own default (None).
        annotation = field.annotation
        origin = getattr(annotation, "__origin__", None)
        if origin is not None:
            args = getattr(annotation, "__args__", ())
            if type(None) in args:
                continue
        elif annotation is type(None):
            continue

        kwargs[name] = _sample_for(annotation, name)
    return schema(**kwargs)


class MockProvider:
    """Deterministic LLM provider for tests and local development."""

    name = "mock"

    def __init__(
        self,
        responses: dict[type[BaseModel], BaseModel] | None = None,
        *,
        model: str = "mock-model",
        fail_with: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self._responses = dict(responses or {})
        self._model = model
        self._fail_with = fail_with
        self._delay_seconds = delay_seconds
        # Every call is recorded so tests can assert on the prompt.
        self.calls: list[dict[str, Any]] = []

    # ---------- configuration ----------

    def set_response(self, schema: type[BaseModel], value: BaseModel) -> None:
        """Register the value to return for a given schema type."""
        self._responses[schema] = value

    # ---------- LLMProvider protocol ----------

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: type[SchemaT],
        timeout_seconds: float,
    ) -> tuple[SchemaT, LLMMetadata]:
        self.calls.append(
            {"system": system, "user": user, "schema": schema.__name__}
        )

        if self._delay_seconds:
            # Cap the simulated delay at the timeout so we don't hang
            # tests that pass a small timeout.
            await asyncio.sleep(min(self._delay_seconds, timeout_seconds + 0.05))

        if self._fail_with is not None:
            raise self._fail_with

        response = self._responses.get(schema)
        if response is None:
            response = _build_default(schema)

        if not isinstance(response, schema):
            raise TypeError(
                f"MockProvider response for {schema.__name__} has wrong type "
                f"(got {type(response).__name__})"
            )

        metadata = LLMMetadata(
            provider=self.name,
            model=self._model,
            input_tokens=128,
            output_tokens=64,
            latency_ms=int(self._delay_seconds * 1000) or 5,
        )
        return response, metadata