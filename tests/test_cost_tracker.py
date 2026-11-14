"""
Definition of done for pricing_table.lookup_price() and UsageTracker. Run with:

    pytest tests/test_cost_tracker.py -v

All of these must pass before moving on to Phase 2.
"""

import pytest

from tollgate.cost.pricing_table import lookup_price
from tollgate.cost.tracker import UsageTracker
from tollgate.providers.base import Usage


# ---------- lookup_price ----------

def test_lookup_price_known_provider_and_model():
    price = lookup_price("anthropic", "claude-haiku-4-5")
    assert price == (1.00, 5.00)


def test_lookup_price_known_provider_unknown_model():
    assert lookup_price("anthropic", "some-model-that-does-not-exist") is None


def test_lookup_price_unknown_provider():
    assert lookup_price("huggingface", "Qwen/Qwen2.5-Coder-32B-Instruct") is None
    assert lookup_price("not-a-real-provider", "whatever") is None


# ---------- UsageTracker ----------

def test_per_call_table_includes_cost_when_known():
    tracker = UsageTracker()
    tracker.record(
        seat_name="architect",
        stage="spec",
        attempt=1,
        provider="anthropic",
        model="claude-haiku-4-5",
        usage=Usage(prompt_tokens=1000, completion_tokens=2000, total_tokens=3000),
    )

    rows = tracker.per_call_table()
    assert len(rows) == 1
    row = rows[0]
    assert row["seat_name"] == "architect"
    assert row["total_tokens"] == 3000
    # (1000/1e6)*1.00 + (2000/1e6)*5.00 = 0.011
    assert row["cost_usd"] == pytest.approx(0.011)


def test_per_call_table_cost_is_none_when_unpriced():
    tracker = UsageTracker()
    tracker.record(
        seat_name="builder",
        stage="code",
        attempt=1,
        provider="huggingface",
        model="Qwen/Qwen2.5-Coder-32B-Instruct",
        usage=Usage(prompt_tokens=500, completion_tokens=500, total_tokens=1000),
    )

    rows = tracker.per_call_table()
    assert rows[0]["cost_usd"] is None


def test_per_run_total_sums_tokens_across_calls():
    tracker = UsageTracker()
    tracker.record(
        seat_name="architect", stage="spec", attempt=1,
        provider="huggingface", model="m",
        usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
    )
    tracker.record(
        seat_name="builder", stage="code", attempt=1,
        provider="huggingface", model="m",
        usage=Usage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
    )

    total = tracker.per_run_total()
    assert total["total_prompt_tokens"] == 300
    assert total["total_completion_tokens"] == 150
    assert total["total_tokens"] == 450


def test_per_run_total_cost_is_none_if_any_call_unpriced():
    tracker = UsageTracker()
    tracker.record(
        seat_name="architect", stage="spec", attempt=1,
        provider="anthropic", model="claude-haiku-4-5",
        usage=Usage(prompt_tokens=1000, completion_tokens=1000, total_tokens=2000),
    )
    tracker.record(
        seat_name="builder", stage="code", attempt=1,
        provider="huggingface", model="m",
        usage=Usage(prompt_tokens=500, completion_tokens=500, total_tokens=1000),
    )

    total = tracker.per_run_total()
    assert total["total_cost_usd"] is None
    assert total["unpriced_tokens"] == 1000


def test_per_run_total_cost_is_float_when_fully_priced():
    tracker = UsageTracker()
    tracker.record(
        seat_name="architect", stage="spec", attempt=1,
        provider="anthropic", model="claude-haiku-4-5",
        usage=Usage(prompt_tokens=1000, completion_tokens=1000, total_tokens=2000),
    )

    total = tracker.per_run_total()
    assert total["total_cost_usd"] == pytest.approx(0.006)  # (1000/1e6)*1.00 + (1000/1e6)*5.00
    assert total["unpriced_tokens"] == 0
