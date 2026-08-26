# Changelog

## 0.2.0 — 2026-08-22

Library release: prefixcash becomes a library you import in your code.

- **Public API** — four verbs as typed functions: `measure_log`, `diagnose_log`,
  `build_heatmap` / `lint` (fix), `run_experiment` (prove), plus re-exports of
  the full model layer (`CacheMetrics`, `Finding`, `Report`, ...).
- **Drop-in integration** — `PrefixCashCallback` for LiteLLM (collect metrics
  from production traffic), `iter_jsonl` / `iter_calls` for dumps.
- **Diagnostics** — intra-session prefix-breakage detection (D21): where the
  prefix diverges between calls and what breaks it; prefix heatmap; assembly
  suggestions (advisory, D18).
- **Optimization (advisory)** — batch ordering by shared prefix (free warm-up,
  zero extra tokens, D22), cache-aware routing recommendations.
- **Experiments** — staging replay of fix variants with a cache-economics
  verdict (D24/D25; quality is validated by the user's own eval).
- **Benchmark** — 5 scenarios, offline diagnosis verification + live DeepSeek
  run (RESULTS.md).
- **Typing** — mypy clean (`--check-untyped-defs`), ruff clean, 40 tests.
- **CI** — GitHub Actions: lint + types + tests + build; trusted PyPI publish
  on version tags.
