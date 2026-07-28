"""Provider-agnostic LLM client with Pydantic-enforced structured output.

Structured output strategy: ask for JSON matching the schema, validate with
Pydantic, and on failure retry once feeding the validation error back to the
model (see config.STRUCTURED_OUTPUT_RETRIES).
"""

import json
import re
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .. import config
from ..trace import Tracer

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class LLMClient:
    def __init__(self):
        provider = config.detect_provider()
        if provider is None:
            raise RuntimeError(
                "No LLM API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, "
                "GEMINI_API_KEY, or GROQ_API_KEY in the environment or a .env "
                "file (see .env.example)."
            )
        self.provider = provider
        self.model = config.model_name(provider)
        self.temperature = config.TEMPERATURE

        if provider == "openai":
            from openai import OpenAI

            self._client = OpenAI()
        elif provider in config.OPENAI_COMPATIBLE:
            import os

            from openai import OpenAI

            compat = config.OPENAI_COMPATIBLE[provider]
            self._client = OpenAI(
                base_url=compat["base_url"],
                api_key=os.environ[compat["key_env"]],
            )
        else:
            from anthropic import Anthropic

            self._client = Anthropic()

    def settings(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
        }

    def complete(self, system: str, user: str) -> str:
        """Single completion with backoff on transient errors (429/5xx) —
        essential on free-tier providers with tight rate limits."""
        delay = 5.0
        for attempt in range(5):
            try:
                return self._complete_once(system, user)
            except Exception as e:
                status = getattr(e, "status_code", None)
                transient = status in (429, 500, 502, 503, 504)
                if not transient or attempt == 4:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")

    def _complete_once(self, system: str, user: str) -> str:
        if self.provider != "anthropic":
            resp = self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content or ""
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def structured(
        self, system: str, user: str, schema: type[T], tracer: Tracer, step: str
    ) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_full = (
            f"{system}\n\n"
            "Respond with a single JSON object matching this JSON schema exactly. "
            "No prose outside the JSON.\n\n"
            f"{schema_json}"
        )
        prompt = user
        last_error: Exception | None = None
        for attempt in range(1 + config.STRUCTURED_OUTPUT_RETRIES):
            tracer.event("llm_call", step=step, attempt=attempt, **self.settings())
            raw = self.complete(system_full, prompt)
            try:
                parsed = schema.model_validate_json(_strip_fences(raw))
                tracer.event("llm_output", step=step, attempt=attempt, output=parsed.model_dump())
                return parsed
            except (ValidationError, ValueError) as e:
                last_error = e
                tracer.event(
                    "llm_output_invalid", step=step, attempt=attempt, error=str(e), raw=raw
                )
                prompt = (
                    f"{user}\n\nYour previous response failed validation with this "
                    f"error, fix it and respond with valid JSON only:\n{e}"
                )
        raise RuntimeError(f"Structured output failed after retries at step '{step}': {last_error}")


def _strip_fences(raw: str) -> str:
    match = _JSON_BLOCK.search(raw)
    if match:
        return match.group(1).strip()
    return raw.strip()
