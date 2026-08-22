# prefixcash

> **Меряй, диагностируй и чини свой prompt-cache hit rate — и показывай сэкономленные доллары.**

Слой экономики префикс-кеша для LLM-приложений: библиотека + CLI/TUI + LiteLLM-плагин.

- **Measure** — фактический hit rate по провайдерам (OpenAI, Anthropic, DeepSeek, OpenRouter), saved USD vs холодный бейзлайн.
- **Diagnose** — где и почему ломается префикс (`{time}`-плейсхолдеры, TTL-протухание, прокси-перестановки, некеширующие upstream'ы).
- **Fix** — прогрев общих префиксов в TTL, правила сборки промпта, кеш-осведомлённая маршрутизация.
- **Prove** — отчёт «$ сэкономлено» с публичной методологией.

## Статус

**Design** — MVP в разработке (P0: измерение).

## Quick start (план)

```bash
pip install prefixcash
prefixcash init
prefixcash monitor      # TUI: hit rate по провайдерам
prefixcash diagnose     # где рвётся префикс и что чинить
prefixcash report       # отчёт «$ сэкономлено» (MD/HTML)
```

## Roadmap

- **P0:** парсеры OpenAI/DeepSeek, `CacheMetrics`, CLI `monitor`/`report`, LiteLLM callback.
- **P1:** парсеры Anthropic/OpenRouter, `diagnose` (LCP + дифф + детект динамики), rules engine.
- **P2:** keep-alive вормер, assembly-lint, auto-fix, бенчмарк-репорт-карды, релиз.

## Лицензия

MIT — см. [LICENSE](LICENSE).
