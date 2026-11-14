# Phase 1 — Provider Abstraction & Cost Tracking

## The concept

Every multi-agent framework has to talk to an LLM somewhere. The naive way is to call
the Anthropic SDK (or OpenAI's, or whoever's) directly from wherever you need a
completion. The problem: now every piece of code that needs an LLM call is coupled to
one specific vendor's SDK, its specific request/response shape, and its specific
authentication. Swap providers, or test without burning API credits, and you're
rewriting call sites all over the codebase.

The fix is the same one you'll recognize from any "swap the database driver" or "swap
the payment processor" problem: define one interface (`LLMProvider.complete()`), and
make everything above that layer — seats, the orchestrator, tollgates — talk only to
the interface, never to a specific vendor. `providers/base.py` is that interface. It's
given to you, complete, because it's the contract everything else in this project is
built against.

**Why `MockProvider` matters as much as the real ones**: a framework whose tests
require a live Hugging Face key (or worse, a paid Anthropic/OpenAI key) to run is a
framework nobody else can clone and test. `MockProvider` is a fake that satisfies the
exact same interface as a real provider but returns scripted, deterministic responses
instead of calling out to the network. Every test you write from here through Phase 6
— seats, tollgates, the orchestrator's retry loop — will use `MockProvider`, not a real
API. Get this right now and it pays off for the rest of the project.

**Why cost tracking is pluggable, not hardcoded**: you only have a Hugging Face key
right now, and HF's free Inference API doesn't have a meaningful per-token $ price —
there's nothing to report. Anthropic and OpenAI do have published pricing. The
`pricing_table` + `UsageTracker` design has to handle both cases honestly: show a real
$ number when one exists, show "unknown" (not a fabricated zero) when it doesn't. This
is also exactly the kind of design decision that's worth being able to explain in an
interview — "what happens when cost is undefined" is a real edge case, not a nitpick.

## What you're implementing

Three files have `TODO`s. Everything else (the dataclasses, the interface, the test
files, the pricing data) is given — don't modify those, just make the TODOs pass their
tests.

1. **`src/tollgate/providers/mock.py`** — `MockProvider.__init__` and `.complete()`.
2. **`src/tollgate/cost/pricing_table.py`** — `lookup_price()`.
3. **`src/tollgate/cost/tracker.py`** — `UsageTracker.record()`, `.per_call_table()`,
   `.per_run_total()`.

Recommended order: `mock.py` first (it's self-contained), then `pricing_table.py`
(small, and `tracker.py` depends on it), then `tracker.py` last.

## Definition of done

```bash
cd ~/AI_Projects/tollgate
pip install -e ".[dev]"
pytest tests/test_providers_mock.py tests/test_cost_tracker.py -v
```

All tests green. That's it — no partial credit, no "mostly working." When you get
there, come back and I'll scaffold Phase 2 (the real Hugging Face provider, plus the
Anthropic/OpenAI stub adapters).

## Hints, if you get stuck

Try without these first. They're ordered from "nudge" to "fairly direct," per file.

### `mock.py`

<details>
<summary>Hint 1 — what state does the provider need?</summary>

`complete()` gets called multiple times, and each call should return the *next*
scripted response. That means `__init__` can't just store the list — it also needs to
remember *where it is* in that list between calls. Two common ways to do this: keep an
index that increments each call, or convert the list into something you can pop from
(careful with ordering if you do — popping from the front vs. the back of a Python list
gives different orders, and `collections.deque` has an O(1) pop from either end if you
want to avoid `list.pop(0)`'s O(n) cost — not that it matters at this scale, just worth
knowing).
</summary>
</details>

<details>
<summary>Hint 2 — detecting exhaustion</summary>

Whatever state you picked in Hint 1, "exhausted" means "there's nothing left to return."
If you're using an index, that's `index >= len(responses)`. If you're using a structure
you pop from, it's "popping raised `IndexError`" or "the structure is empty" — check
before you pop, don't catch the error after.
</summary>
</details>

<details>
<summary>Hint 3 — token counting</summary>

You don't need a real tokenizer. `len(text.split())` (word count) is a fine stand-in —
the tests only check that counts are positive, that `total == prompt + completion`, and
that a longer input produces a larger `prompt_tokens` than a shorter one. They don't
pin an exact number.
</summary>
</details>

### `pricing_table.py`

<details>
<summary>Hint — nested dict lookups</summary>

`PRICING` is a dict of dicts. Before you index `PRICING[provider][model]`, you need to
check `provider` is actually a key in `PRICING` — otherwise an unknown provider raises
`KeyError` instead of your function returning `None`. `dict.get()` is your friend here;
chaining two `.get()` calls (with a default of `{}` on the first) handles both the
unknown-provider and unknown-model cases in one line.
</summary>
</details>

### `tracker.py`

<details>
<summary>Hint 1 — storage</summary>

A plain `list[UsageRecord]` as an instance attribute, appended to in `record()`, is all
you need. Nothing fancier is required.
</summary>
</details>

<details>
<summary>Hint 2 — computing cost_usd for one record</summary>

`lookup_price(provider, model)` gives you `None` or `(price_in, price_out)` — those
prices are **per million tokens**. For one record: if the lookup is `None`, `cost_usd`
is `None`. Otherwise:
`cost = (prompt_tokens / 1_000_000) * price_in + (completion_tokens / 1_000_000) * price_out`.
You'll need this same calculation in both `per_call_table()` and `per_run_total()` —
consider writing it once as a small private helper method and calling it from both.
</summary>
</details>

<details>
<summary>Hint 3 — per_run_total's "all or nothing" cost rule</summary>

Loop through your records, computing each one's cost_usd via the Hint 2 helper. If
*any* record comes back `None`, the whole run's `total_cost_usd` must be `None` — you
can't honestly report "$0.02 total" when part of that total is actually unknown.
Separately, `unpriced_tokens` should be the sum of `total_tokens` from only the records
where cost was `None` — that's how the report says "plus 1000 tokens at unknown cost"
even when it can't give a dollar figure for the whole run.
</summary>
</details>
