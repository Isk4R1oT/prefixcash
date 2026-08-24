"""Ценовые таблицы провайдеров и расчёт стоимости.

⚠️ PRELIMINARY: цены — оценки на 2026-08-22, ПРОВЕРИТЬ перед релизом.
Методология — в METHODOLOGY.md: бейзлайн = весь инпут по полной цене (консервативно).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from prefixcash.core.metrics import CacheMetrics


@dataclass(frozen=True)
class PriceEntry:
    """Цена модели провайдера (USD за 1M инпут-токенов)."""

    base_input_per_mtok: float   # без кеша
    cached_input_per_mtok: float  # кеш-хит
    ttl_hint: str                 # ориентир TTL (информационно)
    updated: str                  # дата проверки
    source: str                   # источник цены
    verified: bool = False        # False = оценка, требует проверки перед релизом


def _p(
    base: float,
    cached: float,
    ttl: str,
    source: str,
    *,
    verified: bool = False,
    updated: str = "2026-08-22",
) -> PriceEntry:
    """Компактный конструктор PriceEntry (цены проверены 2026-08-22, см. METHODOLOGY.md)."""
    return PriceEntry(base, cached, ttl, updated, source, verified)


# Ключ ("provider", "model"); "default" — фолбэк для неизвестных моделей провайдера.
# verified=True — цена подтверждена источником; verified=False — оценка.
PRICING: dict[tuple[str, str], PriceEntry] = {
    ("openai", "gpt-4o"): _p(2.50, 1.25, "~1h", "tokenmix.ai (cached 50% off)", verified=True),
    ("openai", "gpt-4o-mini"): _p(0.15, 0.075, "~1h", "openai.com/api/pricing", verified=True),
    ("openai", "default"): _p(2.50, 1.25, "~1h", "fallback = gpt-4o-class"),
    ("anthropic", "default"): _p(3.00, 0.30, "5min-1h", "dev.to/claudeguide (read = 0.1x)", verified=True),
    ("deepseek", "deepseek-chat"): _p(0.74, 0.028, "hours", "apidog.com deepseek-v4 (96% off)", verified=True),
    ("deepseek", "deepseek-reasoner"): _p(0.55, 0.14, "hours", "api-docs.deepseek.com (может быть вытеснен V4)"),
    ("deepseek", "default"): _p(0.74, 0.028, "hours", "fallback = deepseek-chat (V4)"),
    ("gemini", "default"): _p(0.75, 0.075, "5min (sliding)", "theneuralbase.com (90% off, Apr 2026)", verified=True),
}


@dataclass(frozen=True)
class CostBreakdown:
    """Стоимость вызова и экономия vs холодный бейзлайн."""

    base_input_cost: float    # $ если бы весь инпут шёл по полной цене
    actual_input_cost: float  # $ с учётом кеш-скидок
    saved_usd: float          # base - actual
    priced: bool              # False = нет цены в таблице


def lookup(
    provider: str,
    model: str,
    table: Mapping[tuple[str, str], PriceEntry] = PRICING,
) -> PriceEntry | None:
    entry = table.get((provider, model))
    if entry is None:
        entry = table.get((provider, "default"))
    if entry is None and provider == "openrouter" and "/" in model:
        # OpenRouter: модель вида "anthropic/claude-sonnet-4" — резолвим реального провайдера
        real_provider, real_model = model.split("/", 1)
        entry = table.get((real_provider, real_model)) or table.get((real_provider, "default"))
    return entry


def cost(
    metrics: CacheMetrics,
    table: Mapping[tuple[str, str], PriceEntry] = PRICING,
) -> CostBreakdown:
    """Считает стоимость вызова и экономию vs бейзлайн (см. METHODOLOGY.md)."""
    entry = lookup(metrics.provider, metrics.model, table)
    if entry is None:
        return CostBreakdown(0.0, 0.0, 0.0, priced=False)
    base = metrics.input_tokens / 1_000_000 * entry.base_input_per_mtok
    actual = (
        metrics.miss_tokens / 1_000_000 * entry.base_input_per_mtok
        + metrics.cache_read_tokens / 1_000_000 * entry.cached_input_per_mtok
    )
    return CostBreakdown(
        base_input_cost=base,
        actual_input_cost=actual,
        saved_usd=base - actual,
        priced=True,
    )
