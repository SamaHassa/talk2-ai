"""LLM provider wrapper.

The rest of the app depends only on the `LLMClient` protocol, so the provider can be swapped
(e.g. an open-source model from Hugging Face in step 4) and tests can use a fake.
"""

import json
import os
from collections.abc import AsyncIterator, Sequence
from typing import Protocol, TypeVar

import anthropic
import openai
from pydantic import BaseModel, ValidationError

from app.config import PROVIDER_PRESETS, Settings

T = TypeVar("T", bound=BaseModel)

Message = dict[str, str]  # {"role": "user" | "assistant", "content": "..."}

# Server-side refusal fallback: if the model declines, the API retries on a fallback model.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    """Raised when the model refuses or returns something unusable."""


class LLMClient(Protocol):
    def stream_text(self, system: str, messages: Sequence[Message]) -> AsyncIterator[str]: ...

    async def parse(self, system: str, messages: Sequence[Message], schema: type[T]) -> T: ...


class ClaudeClient:
    def __init__(self, settings: Settings, client: anthropic.AsyncAnthropic | None = None):
        self.settings = settings
        self.client = client or anthropic.AsyncAnthropic()

    async def stream_text(self, system: str, messages: Sequence[Message]) -> AsyncIterator[str]:
        async with self.client.beta.messages.stream(
            model=self.settings.model or PROVIDER_PRESETS["anthropic"]["model"],
            max_tokens=2000,
            system=system,
            messages=list(messages),
            output_config={"effort": self.settings.chat_effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            async for text in stream.text_stream:
                yield text
            final = await stream.get_final_message()
        if final.stop_reason == "refusal":
            raise LLMError("The model declined to answer this message.")

    async def parse(self, system: str, messages: Sequence[Message], schema: type[T]) -> T:
        response = await self.client.beta.messages.parse(
            model=self.settings.model or PROVIDER_PRESETS["anthropic"]["model"],
            max_tokens=8000,
            system=system,
            messages=list(messages),
            output_format=schema,
            output_config={"effort": self.settings.analysis_effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise LLMError("The model declined to analyse this message.")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise LLMError(f"Structured output was incomplete (stop_reason={response.stop_reason}).")
        return response.parsed_output


class OpenAICompatibleClient:
    """Any provider with an OpenAI-compatible API: Groq, Gemini, Ollama (all usable for free).

    Not every free model supports strict JSON schemas, so structured output works like this:
    1. Put the JSON schema in the system prompt and ask for JSON mode.
    2. Validate the reply with Pydantic.
    3. If validation fails, send the error back once and ask the model to fix it.
    This "validate and repair" loop is the same idea libraries like Instructor use.
    """

    def __init__(self, settings: Settings, client: openai.AsyncOpenAI | None = None):
        preset = PROVIDER_PRESETS[settings.provider]
        self.model = settings.model or preset["model"]
        api_key = settings.api_key or (os.environ.get(preset["key_env"], "") if preset["key_env"] else "") or "not-needed"
        self.client = client or openai.AsyncOpenAI(
            base_url=settings.base_url or preset["base_url"], api_key=api_key, max_retries=2, timeout=60
        )

    @staticmethod
    def _with_system(system: str, messages: Sequence[Message]) -> list[dict]:
        return [{"role": "system", "content": system}, *messages]

    async def stream_text(self, system: str, messages: Sequence[Message]) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model, messages=self._with_system(system, messages),
            stream=True, temperature=0.7, max_tokens=600,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def parse(self, system: str, messages: Sequence[Message], schema: type[T]) -> T:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        full_system = (
            f"{system}\n\nRespond with ONLY a JSON object that matches this JSON schema, "
            f"with no extra text:\n{schema_json}"
        )
        convo = self._with_system(full_system, messages)
        last_error = ""
        for _attempt in range(2):
            response = await self.client.chat.completions.create(
                model=self.model, messages=convo, temperature=0,
                response_format={"type": "json_object"}, max_tokens=2000,
            )
            raw = response.choices[0].message.content or ""
            try:
                return schema.model_validate_json(raw)
            except ValidationError as e:
                last_error = str(e)
                convo += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"That JSON was invalid:\n{last_error}\nReturn the corrected JSON only."},
                ]
        raise LLMError(f"Model did not return valid structured output: {last_error[:300]}")


def make_llm(settings: Settings) -> LLMClient:
    if settings.provider == "anthropic":
        return ClaudeClient(settings)
    if settings.provider in PROVIDER_PRESETS:
        return OpenAICompatibleClient(settings)
    raise ValueError(f"Unknown provider {settings.provider!r}; choose from {list(PROVIDER_PRESETS)}")
