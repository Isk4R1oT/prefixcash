"""Кэш-осведомлённая маршрутизация: кеш-френдливость провайдеров и рекомендации.

Advisory (D18): рекомендации пиннинга — «переключатель», а не «грелка»: решает
TTL-проблему без ночных расходов на keep-alive (D22).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from prefixcash.core.pricing import PRICING


@dataclass(frozen=True)
class ProviderScore:
    """Кеш-френдливость провайдера: скидка на кеш-хит × вес TTL."""

    provider: str
    cache_discount: float  # 1 - cached/base (0..1)
    ttl_hint: str
    score: float


_TTL_WEIGHT: dict[str, float] = {
    "hours": 1.0,
    "~1h": 0.8,
    "5min (sliding)": 0.5,
    "5min-1h": 0.5,
}


def cache_friendliness(table: Mapping[tuple[str, str], object] = PRICING) -> list[ProviderScore]:
    """Рейтинг провайдеров по кеш-френдливости (по entry с model == "default")."""
    scores: dict[str, ProviderScore] = {}
    for (provider, model), entry in table.items():
        if model != "default":
            continue
        base = getattr(entry, "base_input_per_mtok", 0.0)
        cached = getattr(entry, "cached_input_per_mtok", 0.0)
        ttl_hint = getattr(entry, "ttl_hint", "")
        if base <= 0:
            continue
        discount = 1.0 - cached / base
        weight = _TTL_WEIGHT.get(ttl_hint, 0.4)
        scores[provider] = ProviderScore(provider, discount, ttl_hint, discount * weight)
    return sorted(scores.values(), key=lambda s: s.score, reverse=True)


def recommend(pool: list[str] | None = None, table: Mapping[tuple[str, str], object] = PRICING) -> str:
    """Рекомендация: какой провайдер пинить для кеш-чувствительного трафика."""
    ranked = cache_friendliness(table)
    if pool:
        ranked = [s for s in ranked if s.provider in pool]
    if not ranked:
        return "нет данных о провайдерах"
    top = ranked[0]
    return (
        f"{top.provider} (кеш-скидка {top.cache_discount:.0%}, TTL {top.ttl_hint}, "
        f"score {top.score:.2f}) — пинить классы чатов с общим префиксом сюда"
    )
