"""OpenAI provider implementation."""

import os
from typing import List, Optional

from openai import AsyncOpenAI

from .base import LLMProvider, LLMResponse, Message


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for GPT models."""

    SUPPORTED_MODELS = ["gpt-5", "gpt-5.1", "gpt-5.2", "gpt-4o", "gpt-4o-mini"]

    # Models that require max_completion_tokens instead of max_tokens
    NEW_PARAM_MODELS = ["gpt-5", "o1", "o3"]

    # Models that only support temperature=1 (no customization)
    FIXED_TEMP_MODELS = ["gpt-5", "o1", "o3"]

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        super().__init__(model, api_key)
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OpenAI API key required via api_key param or OPENAI_API_KEY env var")
        self._client = AsyncOpenAI(api_key=self._api_key)

    def _uses_new_token_param(self) -> bool:
        """Check if model uses max_completion_tokens instead of max_tokens."""
        return any(self.model.startswith(prefix) for prefix in self.NEW_PARAM_MODELS)

    def _has_fixed_temperature(self) -> bool:
        """Check if model only supports temperature=1 (no customization)."""
        return any(self.model.startswith(prefix) for prefix in self.FIXED_TEMP_MODELS)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response using OpenAI's chat completions API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Build kwargs - newer models use max_completion_tokens
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        # Some models (gpt-5, o1, o3) only support temperature=1
        if not self._has_fixed_temperature():
            kwargs["temperature"] = temperature

        if self._uses_new_token_param():
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

        response = await self._client.chat.completions.create(**kwargs)

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
        """Generate a response using OpenAI's chat completions API with conversation history."""
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        # Build kwargs - newer models use max_completion_tokens
        kwargs = {
            "model": self.model,
            "messages": api_messages,
        }

        # Some models (gpt-5, o1, o3) only support temperature=1
        if not self._has_fixed_temperature():
            kwargs["temperature"] = temperature

        if self._uses_new_token_param():
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

        response = await self._client.chat.completions.create(**kwargs)

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
