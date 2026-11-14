"""
Definition of done for MockProvider. Run with:

    pytest tests/test_providers_mock.py -v

All of these must pass before moving on to Phase 2.
"""

import pytest

from tollgate.providers.base import LLMResponse, Message
from tollgate.providers.mock import MockProvider, MockProviderExhausted


def _msg(text: str) -> list[Message]:
    return [Message(role="user", content=text)]


def test_returns_responses_in_order():
    provider = MockProvider(["first", "second", "third"])

    r1 = provider.complete(_msg("hello"))
    r2 = provider.complete(_msg("hello again"))
    r3 = provider.complete(_msg("one more"))

    assert r1.text == "first"
    assert r2.text == "second"
    assert r3.text == "third"


def test_returns_llm_response_with_correct_model_and_provider():
    provider = MockProvider(["hi"])
    response = provider.complete(_msg("hello"))

    assert isinstance(response, LLMResponse)
    assert response.provider == "mock"
    assert response.model  # non-empty string


def test_usage_token_counts_are_consistent():
    provider = MockProvider(["a short reply"])
    response = provider.complete(_msg("a much longer message with many more words in it"))

    usage = response.usage
    assert usage.prompt_tokens > 0
    assert usage.completion_tokens > 0
    assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens


def test_longer_input_produces_more_prompt_tokens():
    provider = MockProvider(["reply", "reply"])

    short = provider.complete(_msg("hi"))
    long = provider.complete(_msg("this is a much longer message with many more words"))

    assert long.usage.prompt_tokens > short.usage.prompt_tokens


def test_raises_when_responses_exhausted():
    provider = MockProvider(["only one"])
    provider.complete(_msg("hello"))

    with pytest.raises(MockProviderExhausted):
        provider.complete(_msg("hello again"))
