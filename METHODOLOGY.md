# prefixcash — Measurement Methodology

**Version 1.0 · 2026-08-22**

> Principle (D9): *we show the method, not just the numbers.* Every number in a
> prefixcash report is reproducible and auditable — no badge claims without a
> documented method.

## 1. Purpose and scope

`prefixcash` measures the economics of LLM prompt/prefix caching and diagnoses
why cache hit rates are low. This document defines exactly how every number is
computed so reports are trustworthy for engineers and for the people who pay the
inference bill.

## 2. Definitions

| Term | Meaning |
|---|---|
| Prefix cache (KV cache) | Provider-side caching of attention states, keyed by an **exact token prefix** of the prompt. |
| Cache hit tokens | Input tokens served from cache (reported by the provider in `usage`). |
| Cache write tokens | Input tokens that created/refreshed a cache entry (Anthropic reports separately). |
| Miss tokens | Input tokens billed at full price. |
| Hit rate | `cache_read_tokens / input_tokens` (per call; token-weighted when aggregated). |
| TTL | Cache lifetime without access; provider- and prefix-length-dependent. |
| Baseline | The conservative counterfactual: **all input tokens at full (uncached) price**. |

## 3. What we parse (provider usage fields)

| Provider | Cache-hit field | Cache-write field | Cache type |
|---|---|---|---|
| OpenAI | `usage.prompt_tokens_details.cached_tokens` | — | automatic |
| Anthropic | `usage.cache_read_input_tokens` | `usage.cache_creation_input_tokens` | explicit checkpoints |
| DeepSeek | `usage.prompt_cache_hit_tokens` | — | automatic |
| Gemini | `usageMetadata.cachedContentTokenCount` | — | implicit |
| OpenRouter | passthrough / `usage.native_tokens_prompt_details` | — | depends on upstream |

LiteLLM normalizes usage to OpenAI-style fields; `prefixcash` parses both raw
provider payloads and LiteLLM-normalized usage.

## 4. Hit rate

```
hit_rate = cache_read_tokens / input_tokens
```

Aggregated hit rate is token-weighted (sum of hits / sum of inputs), not
call-weighted.

## 5. Cost and savings

```
base_input_cost    = input_tokens        × base_input_price
actual_input_cost  = miss_tokens         × base_input_price
                   + cache_read_tokens   × cached_input_price
saved_usd          = base_input_cost − actual_input_cost
```

Pricing lookup: exact `(provider, model)` → provider `"default"` fallback → for
OpenRouter, resolve the real provider from the model prefix (e.g.
`anthropic/claude-sonnet-4` → Anthropic pricing).

**P0 limitation:** cache *write* tokens (Anthropic) are not priced separately;
they are counted as plain input. Only cache reads get the discounted price.

## 6. Pricing tables

- Structure: `(provider, model)` → `{base_input_per_mtok, cached_input_per_mtok, ttl_hint, updated, source, verified}`.
- **`verified=True`** — the price was confirmed against the cited source on the
  date in `updated`. **`verified=False`** — an estimate; never presented as fact.
- Update cadence: prices are re-checked at every release; sources are cited inline.
- Current TTL hints (2026-08-22):

| Provider | TTL hint | Cache discount (verified) |
|---|---|---|
| OpenAI | ~1 h | cached input = 50% of base (gpt-4o class) |
| Anthropic | 5 min–1 h (longer for ≥1024-token prefixes) | cache read = 0.1× base (90% off) |
| DeepSeek | hours | V4: cache hit ≈ 96% off |
| Gemini | 5 min sliding (resets on each access) | cached = 0.1× base (90% off) |
| OpenRouter | depends on upstream | passthrough |

Prices are USD per 1M input tokens.

## 7. Attribution

Metrics are attributed by `session_id` / `agent` / `project` tags passed through
metadata (LiteLLM `litellm_params.metadata`, or record fields in imported logs).
Only provider-reported `usage` fields feed the numbers — no self-reported data.

## 8. Confidence intervals

Planned (P2): bootstrap confidence intervals for hit rate over sessions.
Reports in P0/P1 show point estimates only.

## 9. Prompt-level diagnostics (P1)

- **Tokenization is approximate** (whitespace/word-level), NOT equivalent to the
  provider's BPE tokenizer. It is used only to locate prefix breakage and to
  classify causes — never to compute token counts.
- **Intra-session analysis** (the core of `diagnose`): consecutive calls of the
  same session are compared by their prompts. The first divergent word marks the
  breakage point; the words after it are classified (timestamps, dates, UUIDs,
  numbers, placeholders, emails, URLs with query params, high-entropy segments)
  or reported as plain content change.
- **Usage-level check:** if two calls share a prefix but usage reports zero cache
  hits, the likely causes are TTL expiry or a non-caching provider/upstream
  (recommendation: keep-alive warm-up, P2).
- **All fixes are advisory (D18):** the tool proposes variants; nothing that
  changes a prompt is applied automatically.

## 10. Advisory-first principle (D18)

Changing a prompt affects agent quality. `prefixcash` shows what is wrong and
proposes fix variants. Concrete changes are applied only after the user validates
them (staging experiment, P2). Keep-alive (P2) does not modify prompts and may
run automatically.

## 11. Limitations

- Prices change; re-verify at each release (sources inline).
- Approximate tokenization ≠ BPE (see §9).
- OpenRouter pricing is passthrough; resolved via model prefix when possible.
- Unknown models fall back to the provider `"default"` price; reports expose how
  many calls were priced (`priced_calls`).
- Failed calls carry no `usage` and are excluded (P0).
- Batch, promotion and enterprise discounts are not modelled.

## 12. Changelog

- **2026-08-22** — v1.0. Prices verified: OpenAI gpt-4o/gpt-4o-mini (cached 50%
  off), Anthropic cache read 0.1×, DeepSeek V4 (~96% cache-hit discount),
  Gemini (90% off cached, 5 min sliding TTL, ≥1024 cacheable tokens).
