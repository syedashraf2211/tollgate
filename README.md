# Tollgate

Multi-agent orchestration framework for LLM pipelines — configurable seats, pluggable quality gates, and built-in cost tracking.

```
Architect ──► Builder ──► Reviewer
              ↑               │
              └── Tollgate ◄──┘
                (quality gate)
```

Each agent occupies a **seat** (a role with a system prompt and an LLM provider). Between seats, a **tollgate** evaluates the output against configurable criteria before the next agent runs. If the gate fails, the pipeline retries or escalates — it never silently passes bad output downstream.

## Why this exists

LLM pipelines break in predictable ways: agents hallucinate, ignore instructions, or produce structurally invalid output. Catching this inside the pipeline — before it reaches the next agent or the user — is cheaper and more reliable than post-hoc filtering. Tollgate makes quality gates a first-class primitive rather than an afterthought.

## Architecture

```
providers/          LLM backends — one interface, any backend
  base.py           LLMProvider ABC: .complete(messages) → LLMResponse
  mock.py           Deterministic test double (no API key needed)
  hf.py             Hugging Face Inference API  [phase 2]
  anthropic.py      Anthropic Claude adapter     [phase 2]
  openai.py         OpenAI adapter               [phase 2]

cost/               Token usage and $ cost tracking
  pricing_table.py  Per-provider pricing (None for unpriced providers)
  tracker.py        UsageTracker: per-call table + run totals

seats/              Agent roles                  [phase 3]
tollgate/           Quality gate definitions     [phase 3]
orchestrator/       Seat sequencing + retry loop [phase 4]
```

## Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Provider abstraction, MockProvider, cost tracking | ✅ 13/13 tests |
| 2 | HuggingFace provider, Anthropic/OpenAI stubs, thin agent run | 🔨 in progress |
| 3 | Seat + tollgate pattern, configurable quality gates | pending |
| 4 | Architect → Builder → Reviewer pipeline with retry loop | pending |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

All 13 Phase 1 tests pass with no API key required — `MockProvider` returns scripted responses deterministically.

## Usage (Phase 1)

```python
from tollgate.providers.mock import MockProvider
from tollgate.cost.tracker import UsageTracker
from tollgate.providers.base import Message

provider = MockProvider(["The answer is 42.", "Done."])
tracker = UsageTracker()

messages = [Message(role="user", content="What is the answer?")]
response = provider.complete(messages)

tracker.record(
    seat_name="architect",
    stage="spec",
    attempt=1,
    provider=response.provider,
    model=response.model,
    usage=response.usage,
)

print(response.text)          # "The answer is 42."
print(tracker.per_run_total()) # total tokens, cost (None for mock)
```

## Design decisions

**Why `None` instead of `0` for unknown cost** — Hugging Face's free Inference API has no published per-token price. Returning `0` would make a run that mixed HF and Anthropic calls report a falsely low total cost. `None` propagates: if any call in a run is unpriced, `total_cost_usd` is `None` and `unpriced_tokens` tells you how many tokens had no known price.

**Why provider abstraction** — the orchestrator, seats, and tollgates never import an SDK directly. They call `provider.complete(messages)`. Swapping from MockProvider to HuggingFaceProvider in tests requires changing one line.

**Why MockProvider uses a cursor, not `pop`** — `list.pop(0)` is O(n). A cursor index is O(1) and preserves the original list for inspection after the test.

## License

MIT
