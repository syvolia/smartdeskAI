"""OpenAI-backed LLM provider using structured outputs."""

import asyncio
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)
from pydantic import BaseModel

from app.ai.exceptions import (
    AIInvalidResponseError,
    AITimeoutError,
    AIUnavailableError,
)
from app.ai.provider import LLMMetadata, SchemaT


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
    ) -> None:
        # We create the client without a fixed timeout and enforce
        # per-call timeouts with asyncio.wait_for so callers can tune
        # the budget per operation.
        self._client = AsyncOpenAI(api_key=api_key, max_retries=1)
        self._model = model

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: type[SchemaT],
        timeout_seconds: float,
    ) -> tuple[SchemaT, LLMMetadata]:
        started = time.monotonic()
        try:
            completion = await asyncio.wait_for(
                self._client.beta.chat.completions.parse(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format=schema,
                    temperature=0.2,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise AITimeoutError() from exc
        except APITimeoutError as exc:
            raise AITimeoutError() from exc
        except APIConnectionError as exc:
            raise AIUnavailableError() from exc
        except APIStatusError as exc:
            # 4xx/5xx from OpenAI; treat auth/rate errors as unavailable.
            raise AIUnavailableError() from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        choice = completion.choices[0] if completion.choices else None
        parsed: BaseModel | None = (
            choice.message.parsed if choice and choice.message else None
        )
        if parsed is None:
            raise AIInvalidResponseError()

        if not isinstance(parsed, schema):
            raise AIInvalidResponseError()

        usage = getattr(completion, "usage", None)
        metadata = LLMMetadata(
            provider=self.name,
            model=self._model,
            input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
            latency_ms=latency_ms,
        )
        return parsed, metadata