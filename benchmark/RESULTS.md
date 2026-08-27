# prefixcash benchmark — report cards

Date: 2026-08-27T19:43 · provider: DeepSeek (deepseek-chat) · 
automatic-cache threshold: prefix ≥ ~1024 tokens (verified separately).

| scenario | diagnosis | hit% baseline | hit% fixed | Δ | saved $ (sample) | verdict |
|---|---:|---:|---:|---:|---:|---|
| sales-timestamp | dynamic_iso_datetime | 65.2% | 97.8% | +32.6% | $0.0082 | FIX WORKS |
| sales-uuid | dynamic_uuid | 65.7% | 98.3% | +32.6% | $0.0082 | FIX WORKS |
| kb-reorder | content_change | 49.4% | 98.7% | +49.3% | $0.0082 | FIX WORKS |
| short-prompt | — | 0.0% | 0.0% | +0.0% | $0.0000 | NO GAIN |
| real-framework | dynamic_iso_datetime | 50.3% | 99.0% | +48.6% | $0.0055 | FIX WORKS |

Notes:
- Diagnosis — offline diagnose verification (`benchmark/verify_diagnose.py`).
- `short-prompt` — intentional negative case: cache does not engage on short prompts.
- Savings are for the benchmark sample; extrapolate to production by your own load.
- Numbers depend on provider cache state (TTL) and run order (see METHODOLOGY.md).
