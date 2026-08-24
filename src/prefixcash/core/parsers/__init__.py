"""Реестр парсеров usage провайдеров и фабрика CacheMetrics."""

from __future__ import annotations

from collections.abc import Mapping

from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.parsers.anthropic import AnthropicUsageParser
from prefixcash.core.parsers.base import ParsedUsage, UsageParser
from prefixcash.core.parsers.deepseek import DeepSeekUsageParser
from prefixcash.core.parsers.gemini import GeminiUsageParser
from prefixcash.core.parsers.openai import OpenAIUsageParser
from prefixcash.core.parsers.openrouter import OpenRouterUsageParser

PARSERS: dict[str, UsageParser] = {
    "openai": OpenAIUsageParser(),
    "anthropic": AnthropicUsageParser(),
    "deepseek": DeepSeekUsageParser(),
    "gemini": GeminiUsageParser(),
    "openrouter": OpenRouterUsageParser(),
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
    """Фабрика CacheMetrics из usage-пейлоада провайдера.

    Умный диспатч: провайдер-специфичные поля приоритетны (raw payload), всё
    остальное — в т.ч. LiteLLM-нормализованный usage — парсится в openai-стиле.
    Имя провайдера всегда сохраняется для атрибуции и цен.
    """
    provider = provider.lower()
    if "prompt_cache_hit_tokens" in usage and provider == "deepseek":
        parsed = DeepSeekUsageParser().parse(usage)
    elif "usageMetadata" in usage and provider == "gemini":
        parsed = GeminiUsageParser().parse(usage)
    elif "cache_read_input_tokens" in usage and provider == "anthropic":
        parsed = AnthropicUsageParser().parse(usage)
    elif "native_tokens_prompt_details" in usage and provider == "openrouter":
        parsed = OpenRouterUsageParser().parse(usage)
    else:
        parsed = OpenAIUsageParser().parse(usage)
    return CacheMetrics(
        provider=provider,
        model=model,
        input_tokens=parsed.input_tokens,
        cache_read_tokens=parsed.cache_read_tokens,
        cache_write_tokens=parsed.cache_write_tokens,
        output_tokens=parsed.output_tokens,
        session_id=session_id,
        agent=agent,
        project=project,
    )
