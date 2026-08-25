# prefixcash

> **Меряй, диагностируй и чини свой prompt-cache hit rate — и показывай сэкономленные доллары.**

Слой экономики префикс-кеша для LLM-приложений: библиотека + CLI/TUI + LiteLLM-плагин.

- **Measure** — фактический hit rate по провайдерам (OpenAI, Anthropic, DeepSeek, OpenRouter), saved USD vs холодный бейзлайн.
- **Diagnose** — где и почему ломается префикс (`{time}`-плейсхолдеры, TTL-протухание, прокси-перестановки, некеширующие upstream'ы).
- **Fix** — варианты фиксов (advisory): прогрев общих префиксов в TTL, правила сборки промпта, кеш-осведомлённая маршрутизация — применяются после проверки.
- **Prove** — отчёт «$ сэкономлено» с публичной методологией.

## Статус

**P0 (measure) готов** — парсеры OpenAI/DeepSeek, `CacheMetrics`, CLI, LiteLLM callback, тесты. **P1 (diagnose)** — следующий этап.

## Quick start (из репозитория)

```bash
uv sync --extra dev
uv run prefixcash providers                             # таблица цен/TTL
uv run prefixcash report --file examples/sample.jsonl   # отчёт «$ сэкономлено»
uv run prefixcash monitor --file examples/sample.jsonl
uv run prefixcash diagnose --file examples/diagnose.jsonl  # что ломает префикс внутри сессий
uv run prefixcash tui --file examples/diagnose.jsonl       # интерактивная тепловая карта (j/k — сессии)
```

(PyPI-релиз — на этапе P2. Методология измерений — [METHODOLOGY.md](METHODOLOGY.md).)

## Roadmap

- **P0 (готов):** парсеры OpenAI/DeepSeek, `CacheMetrics`, CLI `monitor`/`report`/`providers`/`import`, LiteLLM callback, тесты.
- **P1 (в работе):** парсеры Anthropic/Gemini/OpenRouter; `diagnose` — внутрисессионный детект поломки префикса (D21); rules engine (advisory-варианты); Textual TUI — остаток.
- **P2 (в работе):** тепловая карта префикса + фикс-предложения (D23); батч-порядок по префиксу вместо keep-alive (D22); кеш-осведомлённая маршрутизация; Textual TUI; эксперименты в staging; бенчмарк-репорт-карды; PyPI/GitHub-релиз.

## Эксперименты в staging (experiment.py)

Проверка фикс-вариантов на выборке: hit rate + $ экономии — до прода (advisory, D18). Качество фиксов проверяется вашим eval'ом (D25).

```bash
export DEEPSEEK_API_KEY=sk-...        # или cp examples/.env.example examples/.env
uv sync --extra dev --extra examples
uv run python -m examples.sales_agent            # агент на LangChain (один ход)
uv run python -m examples.run_experiment         # broken vs fixed: hit rate + экономия
uv run python -m benchmark.verify_diagnose       # офлайн-проверка диагностики (без сети)
uv run python -m benchmark.run_benchmark         # живой прогон -> benchmark/RESULTS.md
```

## Бенчмарк (живой прогон, DeepSeek)

Диагностика находит поломки во всех сценариях; реплей подтверждает экономику фиксов:

| сценарий | диагноз | hit% baseline | hit% fixed | Δ | вердикт |
|---|---|---:|---:|---:|---|
| sales-timestamp | dynamic_iso_datetime | 65% | 87% | +22% | ФИКС ЭФФЕКТИВЕН |
| sales-uuid | dynamic_uuid | 66% | 98% | +33% | ФИКС ЭФФЕКТИВЕН |
| kb-reorder | content_change | 49% | 99% | +49% | ФИКС ЭФФЕКТИВЕН |
| short-prompt | — | 0% | 0% | 0% | ФИКС НЕ ДАЁТ ВЫИГРЫША |
| real-framework (claude-quant L2) | dynamic_iso_datetime | 50% | 75% | +24% | ФИКС ЭФФЕКТИВЕН |

Подробности и $ экономии на выборке: [benchmark/RESULTS.md](benchmark/RESULTS.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
