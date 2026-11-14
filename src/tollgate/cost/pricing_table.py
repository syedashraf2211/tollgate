"""
A table of $-per-million-token pricing, keyed by provider and model.

WHY THIS MATTERS: the framework tracks token usage for every provider, but only some
providers (Anthropic, OpenAI) have a known $ cost per token. Hugging Face's free
Inference API doesn't, so cost for it should come back as "unknown" rather than a
fabricated number — that's what `lookup_price` returning `None` signals to the caller.

The table itself is given to you (it's just data). Your job is the lookup function below.
"""

# provider -> model -> (price_per_million_input_tokens_usd, price_per_million_output_tokens_usd)
PRICING: dict[str, dict[str, tuple[float, float]]] = {
    "anthropic": {
        "claude-opus-4-8": (5.00, 25.00),
        "claude-sonnet-5": (3.00, 15.00),
        "claude-haiku-4-5": (1.00, 5.00),
    },
    "openai": {
        "gpt-4.1": (2.00, 8.00),
        "gpt-4.1-mini": (0.40, 1.60),
    },
    "huggingface": {},  # intentionally empty: cost is always unknown for this provider
}


def lookup_price(provider: str, model: str) -> tuple[float, float] | None:
    """
    Look up (input_price_per_million, output_price_per_million) for a provider+model.

    Returns None if the provider or model isn't in the table — this is the normal,
    expected case for Hugging Face, and callers must handle it (see tracker.py),
    not treat it as an error.

    TODO: implement the lookup. Think about what happens if `provider` itself isn't
    a key in PRICING at all, not just if the model is missing under a known provider.
    """
    if provider not in PRICING:
        return None
    if model not in PRICING[provider]:
        return None
    return PRICING[provider][model]
    #raise NotImplementedError
