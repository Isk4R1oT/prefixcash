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
    updated: str = "2026-08-27",
) -> PriceEntry:
    """Компактный конструктор PriceEntry (даты проверки — в колонке updated)."""
    return PriceEntry(base, cached, ttl, updated, source, verified)


# Ключ ("provider", "model"); "default" — фолбэк для неизвестных моделей провайдера.
# verified=True — цена подтверждена источником; verified=False — оценка.
PRICING: dict[tuple[str, str], PriceEntry] = {
    # OpenAI: текущие модели дают cached input 0.1x базовой (раньше было 0.5x).
    ("openai", "gpt-5.6-sol"): _p(4.00, 0.40, "~1h", "platform.openai.com/docs/pricing", verified=True),
    ("openai", "gpt-5.6-cyber"): _p(12.50, 1.25, "~1h", "platform.openai.com/docs/pricing", verified=True),
    ("openai", "gpt-4o"): _p(2.50, 1.25, "~1h", "legacy: cached = 0.5x", verified=True, updated="2026-08-22"),
    ("openai", "default"): _p(4.00, 0.40, "~1h", "fallback = gpt-5.6-sol"),
    ("anthropic", "default"): _p(3.00, 0.30, "5min-1h", "cache read = 0.1x базовой", verified=True),
    # DeepSeek: указаны PEAK-ставки (off-peak ровно вдвое дешевле, 01:00-04:00
    # и 06:00-10:00 UTC пн-пт — peak). Считаем по peak, чтобы не завышать экономию.
    ("deepseek", "deepseek-v4-flash"): _p(
        0.44, 0.014, "hours", "api-docs.deepseek.com (peak)", verified=True
    ),
    ("deepseek", "deepseek-v4-pro"): _p(
        1.32, 0.044, "hours", "api-docs.deepseek.com (peak)", verified=True
    ),
    ("deepseek", "deepseek-chat"): _p(0.44, 0.014, "hours", "алиас -> deepseek-v4-flash", verified=True),
    ("deepseek", "default"): _p(0.44, 0.014, "hours", "fallback = deepseek-v4-flash"),
    ("gemini", "default"): _p(
        0.75, 0.075, "5min (sliding)", "theneuralbase.com (90% off)", verified=True, updated="2026-08-22"
    ),
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
