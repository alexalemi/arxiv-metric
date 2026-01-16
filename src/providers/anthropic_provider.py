"""Anthropic provider implementation."""

import os
from typing import List, Optional

from anthropic import AsyncAnthropic

from .base import LLMProvider, LLMResponse, Message


class AnthropicProvider(LLMProvider):
    """Anthropic API provider for Claude models."""

    SUPPORTED_MODELS = ["claude-sonnet-4-5-20250929", "claude-opus-4-5-20251101", "claude-haiku-4-5-20251001", "claude-sonnet-4-5", "claude-opus-4-5", "claude-haiku-4-5"]

    def __init__(self, model: str = "claude-sonnet-4-5", api_key: Optional[str] = None):
        super().__init__(model, api_key)
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError("Anthropic API key required via api_key param or ANTHROPIC_API_KEY env var")
        self._client = AsyncAnthropic(api_key=self._api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using Anthropic's messages API."""
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Anthropic requires temperature in [0, 1]
        kwargs["temperature"] = min(max(temperature, 0.0), 1.0)

        response = await self._client.messages.create(**kwargs)

        content = ""
        if response.content:
            content = response.content[0].text if hasattr(response.content[0], "text") else str(response.content[0])

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.provider_name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason,
            raw_response=response.model_dump(),
        )

    async def generate_with_history(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using Anthropic's messages API with conversation history."""
        api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": api_messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Anthropic requires temperature in [0, 1]
        kwargs["temperature"] = min(max(temperature, 0.0), 1.0)

        response = await self._client.messages.create(**kwargs)

        content = ""
        if response.content:
            content = response.content[0].text if hasattr(response.content[0], "text") else str(response.content[0])

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.provider_name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason,
            raw_response=response.model_dump(),
        )
