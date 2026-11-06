"""LLM providers behind one function: complete_json(system, user, schema) -> validated model or None.

- anthropic   : Claude via the Anthropic SDK (structured output with a Pydantic schema)
- openai      : OpenAI
- groq        : Groq (OpenAI-compatible endpoint)
- openrouter  : OpenRouter (OpenAI-compatible endpoint, any model it hosts)

No provider is privileged. Choose with --provider/--model or LLM_PROVIDER/LLM_MODEL in .env; if neither
is set, the first provider with an API key in the environment is used, and with no keys the tool runs
rules-only. Any failure returns None so the caller falls back to rules.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    key_env: str
    default_model: str
    base_url: str | None = None  # None = SDK default


# Default models are starting points; check each provider's current model list and override with --model.
PROVIDERS = {
    "anthropic": ProviderInfo("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-5-5"),
    "openai": ProviderInfo("openai", "OPENAI_API_KEY", "gpt-4.1-mini"),
    "groq": ProviderInfo("groq", "GROQ_API_KEY", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1"),
    "openrouter": ProviderInfo("openrouter", "OPENROUTER_API_KEY", "openai/gpt-4.1-mini", "https://openrouter.ai/api/v1"),
}
@dataclass
class LLMConfig:
    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


def detect_provider() -> str | None:
    """No hard-coded default: LLM_PROVIDER if set, else the first provider with an API key in the env, else None."""
    explicit = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    return next((name for name, info in PROVIDERS.items() if os.getenv(info.key_env)), None)


def resolve(provider: str | None = None, model: str | None = None) -> LLMConfig | None:
    """Flag > LLM_PROVIDER > first provider with a key. Returns None when nothing is configured (rules only)."""
    name = (provider or detect_provider() or "").strip().lower()
    if not name:
        return None
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider '{name}'. Choose one of: {', '.join(PROVIDERS)}")
    chosen_model = model or os.getenv("LLM_MODEL") or PROVIDERS[name].default_model
    return LLMConfig(name, chosen_model)


def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


def _anthropic_json(cfg: LLMConfig, system: str, user: str, schema: type[T], client=None) -> T | None:
    import anthropic

    try:
        client = client or anthropic.Anthropic()
        resp = client.messages.parse(
            model=cfg.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
        )
    except (anthropic.AnthropicError, TypeError) as e:
        _warn(f"{cfg.label} failed: {e}")
        return None
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        _warn(f"{cfg.label} returned no usable output (stop_reason={resp.stop_reason})")
        return None
    return resp.parsed_output


def _openai_compatible_json(cfg: LLMConfig, system: str, user: str, schema: type[T], client=None) -> T | None:
    """JSON mode works across OpenAI, Groq and most OpenRouter models; we validate with Pydantic ourselves."""
    from openai import OpenAI, OpenAIError

    info = PROVIDERS[cfg.provider]
    schema_hint = (
        "\n\nRespond with ONLY a JSON object that matches this JSON Schema, no prose:\n"
        + json.dumps(schema.model_json_schema())
    )
    if client is None and not os.getenv(info.key_env):
        _warn(f"{cfg.label}: {info.key_env} is not set (add it to .env)")
        return None
    try:
        client = client or OpenAI(api_key=os.getenv(info.key_env), base_url=info.base_url)
        resp = client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "system", "content": system + schema_hint}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        return schema.model_validate_json(content)
    except (OpenAIError, ValidationError, IndexError) as e:
        _warn(f"{cfg.label} failed: {e}")
        return None


def complete_json(cfg: LLMConfig, system: str, user: str, schema: type[T], client=None) -> T | None:
    if cfg.provider == "anthropic":
        return _anthropic_json(cfg, system, user, schema, client)
    return _openai_compatible_json(cfg, system, user, schema, client)
