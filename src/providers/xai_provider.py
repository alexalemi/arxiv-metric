"""xAI/Grok provider implementation."""

import os
from typing import List, Optional

from openai import AsyncOpenAI

from .base import LLMProvider, LLMResponse, Message


class XAIProvider(LLMProvider):
    """xAI API provider for Grok models."""

    SUPPORTED_MODELS = ["grok-4", "grok-4-fast-reasoning", "grok-4-fast-non-reasoning", "grok-3", "grok-3-mini", "grok-code-fast-1"]

    def __init__(self, model: str = "grok-4", api_key: Optional[str] = None):
        super().__init__(model, api_key)
        self._api_key = api_key or os.environ.get("XAI_API_KEY")
        if not self._api_key:
            raise ValueError("xAI API key required via api_key param or XAI_API_KEY env var")
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url="https://api.x.ai/v1",
        )

    @property
    def provider_name(self) -> str:
        return "xai"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using xAI's chat completions API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=self.provider_name,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason,
            raw_response=response.model_dump(),
        )

    async def generate_with_history(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using xAI's chat completions API with conversation history."""
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=self.provider_name,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason,
            raw_response=response.model_dump(),
        )
