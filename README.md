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
uv run prefixcash providers                            # таблица цен/TTL
uv run prefixcash report --file examples/sample.jsonl  # отчёт «$ сэкономлено»
uv run prefixcash monitor --file examples/sample.jsonl
```

(PyPI-релиз — на этапе P2.)

## Roadmap

- **P0 (готов):** парсеры OpenAI/DeepSeek, `CacheMetrics`, CLI `monitor`/`report`/`providers`/`import`, LiteLLM callback, тесты.
- **P1:** парсеры Anthropic/Gemini/OpenRouter, `diagnose` (LCP + дифф + детект динамики), rules engine (варианты фиксов).
- **P2:** keep-alive вормер, assembly-lint (варианты), эксперименты в staging, бенчмарк-репорт-карды, релиз.

## Лицензия

MIT — см. [LICENSE](LICENSE).
