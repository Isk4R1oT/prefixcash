# RUNBOOK — from zero to saved dollars in ~10 minutes

`prefixcash` is a small library that closes one problem: finding and fixing the
money your LLM app leaks through a broken prompt prefix cache.

The four verbs: **measure → diagnose → fix (advisory) → prove**.

---

## Step 0. Install

```bash
pip install prefixcash        # Python 3.11+
```

## Step 1. Get numbers — two ways (pick one)

**A. No integration, no API key — run on the demo data (60 seconds):**

```bash
pip install prefixcash
uv run prefixcash report --file examples/sample.jsonl      # from the repo, or your own log
```

Expected: a table with hit rate per provider and **$ saved vs cold baseline**.
If your log is in LiteLLM/OpenRouter/raw format, it just works — `report`
accepts provider usage, LiteLLM-normalized usage, and prefixcash's own format.

**B. Production: attach the drop-in LiteLLM callback:**

```python
import litellm
from prefixcash import PrefixCashCallback

litellm.callbacks = [PrefixCashCallback(file="metrics.jsonl")]
# ...your traffic flows... then:
from prefixcash import measure_log
report = measure_log("metrics.jsonl")
print(report.totals.hit_rate, report.totals.saved_usd)
```

## Step 2. Diagnose — where and why the cache breaks

```python
from prefixcash import diagnose_log

for session_id, findings in diagnose_log("metrics.jsonl").items():
    for f in findings:
        print(session_id, f.break_words, [c.kind for c in f.causes])
```

Expected causes: `dynamic_iso_datetime`, `dynamic_time`, `dynamic_uuid`,
`content_change`, `cache_miss_despite_shared_prefix`, ...

Or the CLI with a visual heatmap of the prompt:

```bash
uv run prefixcash diagnose --file metrics.jsonl
uv run prefixcash tui --file metrics.jsonl          # interactive, j/k — sessions
```

## Step 3. Fix (advisory) — nothing is applied automatically (D18)

```python
from prefixcash import iter_calls, build_heatmap, lint, suggest_order, recommend

calls = list(iter_calls("metrics.jsonl"))
hm = build_heatmap(session_id, calls)
for s in lint(hm):                       # assembly suggestions
    print(s.position, s.word, "->", s.suggestion)

order = suggest_order(calls)             # batch order: shared prefixes hit each other
print(recommend())                       # which provider to pin (cache-friendly)
```

The fixes are proposals — validate with your own eval before changing prompts.

## Step 4. Prove — replay a fix variant on a staging sample

```bash
export DEEPSEEK_API_KEY=sk-...
uv run python -m examples.run_experiment    # broken vs fixed: hit rate + $ saved
```

Or in code:

```python
from prefixcash import SessionCase, run_experiment

cases = [SessionCase(session_id="chat-1", system_prompt=sys_prompt, turns=["Q1", "Q2"])]
report = run_experiment(cases, client, prompt_for=my_prompt_builder)
print(report.verdict)    # "FIX WORKS: hit rate 49% -> 98% ..." or "NO GAIN"
```

---

## Mental model

```
usage fields (provider/LiteLLM)  →  measure  →  hit rate + $ saved
prompts (sessions)               →  diagnose →  where the prefix breaks + why
fixes                            →  advisory →  heatmap, assembly, routing, batch order
staging replay                   →  prove    →  verdict (quality is YOUR eval)
```

Where things live: `prefixcash/core` (parsers, pricing), `diagnose` (heatmap,
rules), `optimize` (batch, routing, experiment), `integrations` (LiteLLM
callback, importers), `cli` (report/monitor/diagnose/providers/import/tui).

## Troubleshooting

| Symptom | Likely cause | Do |
|---|---|---|
| hit rate ≈ 0 everywhere | prompts shorter than the cache threshold (~1024 tokens on DeepSeek) | lengthen the static prefix (KB/context), or accept no caching |
| `dynamic_*` findings | dynamic value at the start of the system prompt | move it to the end / metadata |
| `cache_miss_despite_shared_prefix` | TTL expired or non-caching upstream | pin a cache-friendly provider, or keep-alive warm-up (P2) |
| unknown provider in report | model not in pricing tables | add an entry in `prefixcash/core/pricing.py` (see METHODOLOGY) |

## Further reading

- [METHODOLOGY.md](../METHODOLOGY.md) — how every number is computed (verified prices, baseline).
- [benchmark/RESULTS.md](../benchmark/RESULTS.md) — live benchmark report cards.
- [RELEASING.md](RELEASING.md) — how new versions are published.
