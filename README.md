# prefixcash

> **Меряй, диагностируй и чини свой prompt-cache hit rate — и показывай сэкономленные доллары.**

Слой экономики префикс-кеша для LLM-приложений: библиотека + CLI/TUI + LiteLLM-плагин.

- **Measure** — фактический hit rate по провайдерам (OpenAI, Anthropic, DeepSeek, OpenRouter), saved USD vs холодный бейзлайн.
- **Diagnose** — где и почему ломается префикс (`{time}`-плейсхолдеры, TTL-протухание, прокси-перестановки, некеширующие upstream'ы).
- **Fix** — варианты фиксов (advisory): прогрев общих префиксов в TTL, правила сборки промпта, кеш-осведомлённая маршрутизация — применяются после проверки.
- **Prove** — отчёт «$ сэкономлено» с публичной методологией.

## Статус

**Design** — MVP в разработке (P0: измерение).

## Quick start (план)

```bash
pip install prefixcash
prefixcash init
prefixcash monitor      # TUI: hit rate по провайдерам
prefixcash diagnose     # что мешает и варианты фикса
prefixcash report       # отчёт «$ сэкономлено» (MD/HTML)
```

## Roadmap

- **P0:** парсеры OpenAI/DeepSeek, `CacheMetrics`, CLI `monitor`/`report`, LiteLLM callback.
- **P1:** парсеры Anthropic/Gemini/OpenRouter, `diagnose` (LCP + дифф + детект динамики), rules engine (варианты фиксов).
- **P2:** keep-alive вормер, assembly-lint (варианты), эксперименты в staging, бенчмарк-репорт-карды, релиз.

## Лицензия

MIT — см. [LICENSE](LICENSE).
