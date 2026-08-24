"""Реестр парсеров usage провайдеров и фабрика CacheMetrics."""

from __future__ import annotations

from typing import Mapping

from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers.base import ParsedUsage, UsageParser
from prefixcash.core.parsers.deepseek import DeepSeekUsageParser
from prefixcash.core.parsers.openai import OpenAIUsageParser

PARSERS: dict[str, UsageParser] = {
    "openai": OpenAIUsageParser(),
    "deepseek": DeepSeekUsageParser(),
}


class UnsupportedProviderError(ValueError):
    """Провайдер не поддерживается (парсер не зарегистрирован)."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"unsupported provider: {provider!r} (available: {sorted(PARSERS)})")
        self.provider = provider


def parse_usage(provider: str, payload: Mapping) -> ParsedUsage:
    """Парсит usage-пейлоад провайдера в нормализованные поля."""
    parser = PARSERS.get(provider.lower())
    if parser is None:
        raise UnsupportedProviderError(provider)
    return parser.parse(payload)


def to_metrics(
    provider: str,
    model: str,
    usage: Mapping,
    *,
    session_id: str | None = None,
    agent: str | None = None,
    project: str | None = None,
) -> CacheMetrics:
    """Фабрика CacheMetrics из usage-пейлоада провайдера."""
    parsed = parse_usage(provider, usage)
    return CacheMetrics(
        provider=provider.lower(),
        model=model,
        input_tokens=parsed.input_tokens,
        cache_read_tokens=parsed.cache_read_tokens,
        cache_write_tokens=parsed.cache_write_tokens,
        output_tokens=parsed.output_tokens,
        session_id=session_id,
        agent=agent,
        project=project,
    )
