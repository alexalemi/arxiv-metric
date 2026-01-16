"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic', 'google')."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens in response.

        Returns:
            LLMResponse containing the generated content and metadata.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
