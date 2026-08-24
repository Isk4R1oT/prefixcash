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


# Ключ ("provider", "model"); "default" — фолбэк для неизвестных моделей провайдера.
PRICING: dict[tuple[str, str], PriceEntry] = {
    ("openai", "gpt-4o"): PriceEntry(2.50, 1.25, "~1h", "2026-08-22", "https://openai.com/api/pricing/"),
    ("openai", "gpt-4o-mini"): PriceEntry(0.15, 0.075, "~1h", "2026-08-22", "https://openai.com/api/pricing/"),
    ("openai", "default"): PriceEntry(2.50, 1.25, "~1h", "2026-08-22", "https://openai.com/api/pricing/"),
    ("anthropic", "default"): PriceEntry(3.00, 0.30, "5min-1h", "2026-08-22", "https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching"),
    ("deepseek", "deepseek-chat"): PriceEntry(0.27, 0.014, "hours", "2026-08-22", "https://api-docs.deepseek.com/quick_start/pricing"),
    ("deepseek", "deepseek-reasoner"): PriceEntry(0.55, 0.14, "hours", "2026-08-22", "https://api-docs.deepseek.com/quick_start/pricing"),
    ("deepseek", "default"): PriceEntry(0.27, 0.014, "hours", "2026-08-22", "https://api-docs.deepseek.com/quick_start/pricing"),
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
