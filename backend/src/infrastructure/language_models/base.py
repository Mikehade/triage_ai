from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: MessageRole
    content: str


@dataclass
class LLMConfig:
    """
    Model-agnostic generation config.
    Each provider adapter maps these to its own parameter names.
    """
    temperature: float = 0.2        # low by default — clinical context needs consistency
    max_output_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    candidate_count: int = 1


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    raw: Any = None                 # provider-specific raw response — useful for debugging


class ILLMClient(ABC):
    """
    Provider-agnostic LLM interface.
    Swap Gemini for OpenAI/Anthropic/Bedrock by implementing this and
    updating the DI container. Nothing else changes.
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Send a list of messages and return a completion."""
        raise NotImplementedError

    @abstractmethod
    async def complete_json(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> dict:
        """
        Complete and parse the response as JSON.
        Provider implementations should use native JSON mode where available
        (Gemini response_mime_type, OpenAI response_format) rather than
        prompting for JSON and hoping.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Confirm the provider is reachable. Used at startup."""
        raise NotImplementedError