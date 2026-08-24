"""Нормализованные метрики кеша/стоимости одного LLM-вызова (провайдер-агностично)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable


@dataclass
class CacheMetrics:
    """Нормализованные метрики префикс-кеша для одного вызова."""

    provider: str
    model: str
    input_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    session_id: str | None = None
    agent: str | None = None
    project: str | None = None
    ts: datetime = field(default_factory=datetime.utcnow)

    @property
    def miss_tokens(self) -> int:
        """Токены, обслуженные без попадания в кеш."""
        return max(0, self.input_tokens - self.cache_read_tokens)

    @property
    def hit_rate(self) -> float:
        """Доля инпут-токенов из кеша: cache_read / input."""
        if self.input_tokens <= 0:
            return 0.0
        return self.cache_read_tokens / self.input_tokens


@dataclass
class AggregateMetrics:
    """Агрегат по набору вызовов (опционально — фильтр по провайдеру/модели)."""

    provider: str | None = None
    model: str | None = None
    calls: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0

    @property
    def hit_rate(self) -> float:
        if self.input_tokens <= 0:
            return 0.0
        return self.cache_read_tokens / self.input_tokens


def aggregate(
    metrics: Iterable[CacheMetrics],
    *,
    provider: str | None = None,
    model: str | None = None,
) -> AggregateMetrics:
    """Суммирует метрики, опционально фильтруя по провайдеру и/или модели."""
    agg = AggregateMetrics(provider=provider, model=model)
    for m in metrics:
        if provider is not None and m.provider != provider:
            continue
        if model is not None and m.model != model:
            continue
        agg.calls += 1
        agg.input_tokens += m.input_tokens
        agg.cache_read_tokens += m.cache_read_tokens
        agg.cache_write_tokens += m.cache_write_tokens
        agg.output_tokens += m.output_tokens
    return agg
