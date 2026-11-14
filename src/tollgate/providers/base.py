"""
The provider interface every LLM backend (Hugging Face, Anthropic, OpenAI, Mock) implements.

This file is complete, given to you as-is — it's the contract the rest of the framework
is built against. Nothing to implement here; read it before you start on mock.py, because
your MockProvider must satisfy this exact interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    """A single turn in a chat conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class Usage:
    """Token accounting for one LLM call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMResponse:
    """What every provider's `complete()` call returns."""

    text: str
    usage: Usage
    model: str
    provider: str


class LLMProvider(ABC):
    """
    Abstract base for any LLM backend.

    Why this exists: the orchestrator, the Seat class, and everything above this layer
    should never know or care whether they're talking to Hugging Face, Claude, OpenAI, or
    a test double. They only ever call `.complete(messages)` and get back an `LLMResponse`.
    That's the whole point of the abstraction — swap the provider, nothing else changes.
    """

    name: str

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send messages to the backend and return its response with usage info."""
        raise NotImplementedError
