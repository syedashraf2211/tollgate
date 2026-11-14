"""
UsageTracker — aggregates token usage and cost across a pipeline run.

WHY THIS MATTERS: later, the orchestrator will call multiple seats (Architect, Builder,
Reviewer), each possibly multiple times (retries). At the end, the CLI needs to show a
report: how many tokens did this run cost, broken down by seat, and what was the total
$ cost (when known). This class is where that bookkeeping lives.
"""

from dataclasses import dataclass, field

from tollgate.cost.pricing_table import lookup_price
from tollgate.providers.base import Usage


@dataclass
class UsageRecord:
    """One recorded LLM call, tagged with where in the pipeline it happened."""

    seat_name: str
    stage: str
    attempt: int
    provider: str
    model: str
    usage: Usage


class UsageTracker:
    """Records usage per call, then reports it per-call and aggregated for a whole run."""

    def __init__(self):
        self._records: list[UsageRecord] = []

    def record(
        self,
        *,
        seat_name: str,
        stage: str,
        attempt: int,
        provider: str,
        model: str,
        usage: Usage,
    ) -> None:
        """Called once per LLM call made anywhere in a pipeline run."""
        self._records.append(
            UsageRecord(
                seat_name=seat_name,
                stage=stage,
                attempt=attempt,
                provider=provider,
                model=model,
                usage=usage,
            )
        )

    def _cost_usd(self, record: UsageRecord) -> float | None:
        """Cost of one call in USD, or None if the provider/model has no known price."""
        price = lookup_price(record.provider, record.model)
        if price is None:
            return None
        price_in, price_out = price  # $ per million tokens
        return (
            (record.usage.prompt_tokens / 1_000_000) * price_in
            + (record.usage.completion_tokens / 1_000_000) * price_out
        )

    def per_call_table(self) -> list[dict]:
        """
        One row per recorded call, for a detailed CLI table. Each row should include at
        least: seat_name, stage, attempt, provider, model, prompt_tokens,
        completion_tokens, total_tokens, and cost_usd (a float, or None if unpriced —
        use lookup_price() to find out).
        """
        return [
            {
                "seat_name": r.seat_name,
                "stage": r.stage,
                "attempt": r.attempt,
                "provider": r.provider,
                "model": r.model,
                "prompt_tokens": r.usage.prompt_tokens,
                "completion_tokens": r.usage.completion_tokens,
                "total_tokens": r.usage.total_tokens,
                "cost_usd": self._cost_usd(r),
            }
            for r in self._records
        ]

    def per_run_total(self) -> dict:
        """
        A single summary dict for the whole run so far. Must include:
          - total_prompt_tokens, total_completion_tokens, total_tokens (ints, summed)
          - total_cost_usd: a float IF every single record had known pricing,
            otherwise None — don't report a partial total as if it were complete.
          - unpriced_tokens: total_tokens summed across only the records where cost
            was unknown (so the report can say "plus N tokens at unknown cost")
        """
        total_prompt = 0
        total_completion = 0
        total_tokens = 0
        total_cost = 0.0
        unpriced_tokens = 0
        any_unpriced = False

        for r in self._records:
            total_prompt += r.usage.prompt_tokens
            total_completion += r.usage.completion_tokens
            total_tokens += r.usage.total_tokens
            cost = self._cost_usd(r)
            if cost is None:
                any_unpriced = True
                unpriced_tokens += r.usage.total_tokens
            else:
                total_cost += cost

        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "total_cost_usd": None if any_unpriced else total_cost,
            "unpriced_tokens": unpriced_tokens,
        }
