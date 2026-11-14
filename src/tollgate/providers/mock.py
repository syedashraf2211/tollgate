"""
MockProvider — a scripted, deterministic stand-in for a real LLM backend.

WHY THIS MATTERS: every other test in this project (seats, tollgates, the orchestrator's
retry loop) needs to call an LLMProvider without hitting a real API — no network flakiness,
no cost, no non-determinism, and no API key requirement for anyone who clones this repo.
MockProvider is what makes that possible. Every test file after this one will build on it.

See workbook/phase1_providers_and_cost.md for the concept walkthrough and hints.
"""

from sqlite3 import complete_statement
from tollgate.providers.base import LLMProvider, LLMResponse, Message, Usage


class MockProviderExhausted(Exception):
    """Raised when MockProvider.complete() is called more times than it has scripted responses."""


class MockProvider(LLMProvider):
    """
    A provider that returns pre-scripted responses in order, one per call.

    Usage:
        provider = MockProvider(["first response", "second response"])
        provider.complete([...])   # -> LLMResponse(text="first response", ...)
        provider.complete([...])   # -> LLMResponse(text="second response", ...)
        provider.complete([...])   # -> raises MockProviderExhausted
    """

    name = "mock"

    def __init__(self, responses: list[str]):
        # Keep our own copy so later changes to the caller's list can't affect us,
        # plus a cursor for where we are. complete() is called many times, so this
        # state has to live on self to survive between calls.
        self._responses = list(responses)
        self._calls = 0

    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        # 1. Check before taking: if the cursor is past the end, nothing is left.
        if self._calls >= len(self._responses):
            raise MockProviderExhausted(
                f"complete() called {self._calls + 1} times "
                f"but only {len(self._responses)} responses were scripted"
            )
        text = self._responses[self._calls]
        self._calls += 1

        # 2. Word counts stand in for a tokenizer. Prompt covers ALL messages, and
        #    total is derived from the other two so it can never disagree with them.
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        completion_tokens = len(text.split())
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        # 3. Keyword arguments, so the fields can't be swapped by position.
        return LLMResponse(text=text, usage=usage, model="mock-model", provider=self.name)
