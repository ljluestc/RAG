"""Multi-provider LLM router with streaming and fallback support."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from .models import ModelInfo, TokenUsage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Available models registry
# ---------------------------------------------------------------------------

MODELS: List[ModelInfo] = [
    ModelInfo(id="gpt-4o", provider="openai", name="GPT-4o", max_tokens=8192),
    ModelInfo(id="gpt-4o-mini", provider="openai", name="GPT-4o Mini", max_tokens=4096),
    ModelInfo(id="gpt-3.5-turbo", provider="openai", name="GPT-3.5 Turbo", max_tokens=4096),
    ModelInfo(id="claude-sonnet-4-20250514", provider="anthropic", name="Claude Sonnet 4", max_tokens=8192),
    ModelInfo(id="claude-haiku-4-5-20251015", provider="anthropic", name="Claude Haiku 4.5", max_tokens=4096),
]

_MODEL_MAP: Dict[str, ModelInfo] = {m.id: m for m in MODELS}


def get_model_info(model_id: str) -> Optional[ModelInfo]:
    return _MODEL_MAP.get(model_id)


# ---------------------------------------------------------------------------
# Provider base class
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract async LLM provider."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """Return {"content": str, "usage": TokenUsage}."""

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Yield token strings as they arrive."""


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    async def generate(self, messages, model, temperature=0.7, max_tokens=2048):
        resp = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = TokenUsage(
            prompt=resp.usage.prompt_tokens if resp.usage else 0,
            completion=resp.usage.completion_tokens if resp.usage else 0,
            total=resp.usage.total_tokens if resp.usage else 0,
        )
        return {"content": resp.choices[0].message.content or "", "usage": usage}

    async def stream(self, messages, model, temperature=0.7, max_tokens=2048):
        resp = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in resp:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        import anthropic
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )

    async def generate(self, messages, model, temperature=0.7, max_tokens=2048):
        # Separate system message
        system = ""
        chat_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_msgs.append(m)

        resp = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "You are a helpful assistant.",
            messages=chat_msgs,
        )
        usage = TokenUsage(
            prompt=resp.usage.input_tokens,
            completion=resp.usage.output_tokens,
            total=resp.usage.input_tokens + resp.usage.output_tokens,
        )
        return {"content": resp.content[0].text, "usage": usage}

    async def stream(self, messages, model, temperature=0.7, max_tokens=2048):
        system = ""
        chat_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_msgs.append(m)

        async with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "You are a helpful assistant.",
            messages=chat_msgs,
        ) as stream:
            async for text in stream.text_stream:
                yield text


# ---------------------------------------------------------------------------
# Local / mock provider (for testing without API keys)
# ---------------------------------------------------------------------------

class LocalProvider(LLMProvider):
    async def generate(self, messages, model, temperature=0.7, max_tokens=2048):
        content = "This is a local/mock response for testing."
        return {
            "content": content,
            "usage": TokenUsage(prompt=0, completion=len(content) // 4, total=len(content) // 4),
        }

    async def stream(self, messages, model, temperature=0.7, max_tokens=2048):
        for word in "This is a streaming mock response for testing.".split():
            yield word + " "
            await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class LLMRouter:
    """Routes requests to the correct provider with retry + fallback."""

    def __init__(self, settings=None):
        self._providers: Dict[str, LLMProvider] = {}
        self._fallback_chain: List[str] = ["gpt-4o-mini", "gpt-3.5-turbo"]
        self._init_providers(settings)

    def _init_providers(self, settings=None):
        openai_key = (settings.openai_api_key if settings else None) or os.getenv("OPENAI_API_KEY")
        anthropic_key = (settings.anthropic_api_key if settings else None) or os.getenv("ANTHROPIC_API_KEY")

        if openai_key:
            self._providers["openai"] = OpenAIProvider(api_key=openai_key)
        if anthropic_key:
            self._providers["anthropic"] = AnthropicProvider(api_key=anthropic_key)

        # Always register local as fallback
        self._providers["local"] = LocalProvider()

    def _get_provider(self, model_id: str) -> LLMProvider:
        info = get_model_info(model_id)
        if info and info.provider in self._providers:
            return self._providers[info.provider]
        if "local" in self._providers:
            return self._providers["local"]
        raise ValueError(f"No provider available for model {model_id}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        retries: int = 2,
    ) -> Dict[str, Any]:
        """Generate with retry + fallback."""
        models_to_try = [model] + [m for m in self._fallback_chain if m != model]

        last_error: Exception | None = None
        for mid in models_to_try:
            provider = self._get_provider(mid)
            for attempt in range(retries + 1):
                try:
                    result = await provider.generate(messages, mid, temperature, max_tokens)
                    result["model"] = mid
                    return result
                except Exception as exc:
                    last_error = exc
                    logger.warning(f"LLM error (model={mid}, attempt={attempt}): {exc}")
                    if attempt < retries:
                        await asyncio.sleep(0.5 * (attempt + 1))

        raise last_error or RuntimeError("All LLM providers failed")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream tokens from the best available provider."""
        provider = self._get_provider(model)
        async for token in provider.stream(messages, model, temperature, max_tokens):
            yield token

    @property
    def available_models(self) -> List[ModelInfo]:
        available_providers = set(self._providers.keys())
        return [m for m in MODELS if m.provider in available_providers]
