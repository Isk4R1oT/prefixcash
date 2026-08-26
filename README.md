<div align="center">

# prefixcash

**Measure, diagnose and fix your LLM prompt-cache hit rate — and see the dollars you save.**

A cache-economics layer for LLM applications: library + CLI/TUI + LiteLLM plugin.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)
[![PyPI](https://img.shields.io/pypi/v/prefixcash)](https://pypi.org/project/prefixcash/)

</div>

## Why

LLM providers cache attention states by the **exact token prefix** of your prompt. Cache hits cost **50–96% less** on input tokens (OpenAI ~50%, Anthropic ~90%, DeepSeek ~96%, Gemini ~90% — verified prices in [METHODOLOGY.md](METHODOLOGY.md)). Most applications never see those savings:

- every new chat starts with an expensive **cold call**;
- a dynamic `{time}`, UUID or session id at the start of the system prompt **breaks the prefix on every single call**;
- TTLs expire between chats and some providers/upstreams don't cache well;
- **most platforms don't even know their own hit rate.**

`prefixcash` closes the loop: **measure** it, **diagnose** what breaks it, **fix** it safely, **prove** the dollars.

## Features

- **Measure** — real hit rate per provider/model/session from provider `usage` fields (OpenAI, Anthropic, DeepSeek, Gemini, OpenRouter; raw payloads or LiteLLM-normalized), saved USD vs a conservative cold baseline.
- **Diagnose** — intra-session prefix-breakage detection (D21): where in the prompt the prefix diverges between consecutive calls and *what* breaks it (timestamps, UUIDs, reordering, placeholders, high-entropy segments), plus a usage-level check for *"shared prefix but no cache hit"* (TTL expiry / non-caching provider).
- **Fix (advisory, D18)** — the **prefix heatmap** shows exactly where the cache is lost and proposes assembly fixes (static prefix first, dynamic to the end); cache-aware routing recommendations (pin cache-friendly providers); batch-ordering of calls with shared prefixes — **free warm-up from natural traffic, zero extra tokens** (no 24/7 keep-alive pings).
- **Prove** — `report` produces the *«$ saved vs cold baseline»* artifact with a public methodology; `experiment` replays fix variants on a staging sample and gives a cache-economics verdict (quality is validated with your own eval, D25).

## Quick start

```bash
pip install prefixcash        # once published on PyPI
```

From the repo:

```bash
uv sync --extra dev --extra examples
uv run prefixcash providers                              # pricing / TTL table
uv run prefixcash report --file examples/sample.jsonl    # $ saved vs cold baseline
uv run prefixcash diagnose --file examples/diagnose.jsonl  # what breaks the prefix + heatmap + fixes
uv run prefixcash tui --file examples/diagnose.jsonl     # interactive heatmap (j/k — sessions)
```

`diagnose` on a session whose system prompt embeds a changing timestamp:

```
s1 — 2 findings, prefix stability 73%
  call 0 -> 1: shared prefix 5 words
    words after the break: 09:05:00. Отвечай коротко и по делу.
    • dynamic_time: word after the break: '09:05:00.'
    • cache_miss_despite_shared_prefix: shared prefix 5 words, but usage.cache_read_tokens == 0
    → fix: move the dynamic time/timestamp to the END of the prompt (after the static block)
  heatmap (color = prefix stability): ...
```

## Experiments (staging)

Validate fix variants before production: replay a sample against your provider, measure hit rate + saved USD, get a verdict. Quality is checked with **your own eval** (D25).

```bash
export DEEPSEEK_API_KEY=sk-...        # or: cp examples/.env.example examples/.env
uv sync --extra dev --extra examples
uv run python -m examples.sales_agent            # LangChain agent (one turn)
uv run python -m examples.run_experiment         # broken vs fixed: hit rate + savings
uv run python -m benchmark.verify_diagnose       # offline diagnose check (no network)
uv run python -m benchmark.run_benchmark         # live run -> benchmark/RESULTS.md
```

## Benchmark (live run, DeepSeek)

Diagnosis finds every breakage pattern; replay confirms the fix economics:

| scenario | diagnosis | hit% baseline | hit% fixed | Δ | verdict |
|---|---|---:|---:|---:|---|
| sales-timestamp | dynamic_iso_datetime | 65% | 87% | +22% | FIX WORKS |
| sales-uuid | dynamic_uuid | 66% | 98% | +33% | FIX WORKS |
| kb-reorder | content_change | 49% | 99% | +49% | FIX WORKS |
| short-prompt | — | 0% | 0% | 0% | NO GAIN (honest) |
| real-framework (claude-quant L2) | dynamic_iso_datetime | 50% | 75% | +24% | FIX WORKS |

Details and per-sample $: [benchmark/RESULTS.md](benchmark/RESULTS.md).

## Architecture

```
src/prefixcash/
├── core/         # CacheMetrics, provider usage parsers, pricing tables
├── diagnose/     # intra-session breakage detection, prefix heatmap, assembly-lint
├── optimize/     # batch ordering by prefix, cache-aware routing, staging experiments
├── integrations/ # LiteLLM callback, JSONL importers
└── cli/          # report / monitor / diagnose / providers / import / tui
```

Measurement methodology (baseline, pricing policy, TTL, limitations): [METHODOLOGY.md](METHODOLOGY.md).

## Roadmap

- **P0 (measure)** ✅ — parsers (OpenAI/DeepSeek), `CacheMetrics`, report/monitor CLI, LiteLLM callback.
- **P1 (diagnose)** ✅ — parsers (Anthropic/Gemini/OpenRouter), intra-session breakage detection, heatmap.
- **P2 (optimize + launch)** 🚧 — heatmap ✅, batch-order ✅, routing ✅, Textual TUI ✅, experiments ✅, benchmark ✅; **next:** PyPI + GitHub release, benchmark blog post, Show HN.

## Contributing

PRs are welcome — especially new provider parsers and benchmark scenarios. Open an issue first for design discussions.

## License

MIT — see [LICENSE](LICENSE).
