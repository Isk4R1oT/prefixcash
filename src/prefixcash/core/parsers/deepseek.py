"""Парсер usage DeepSeek: usage.prompt_cache_hit_tokens / prompt_cache_miss_tokens."""

from __future__ import annotations

from collections.abc import Mapping

from prefixcash.core.parsers.base import ParsedUsage


class DeepSeekUsageParser:
    provider = "deepseek"

    def parse(self, payload: Mapping) -> ParsedUsage:
        input_tokens = int(payload.get("prompt_tokens", 0) or 0)
        output_tokens = int(payload.get("completion_tokens", 0) or 0)
        cache_hit = int(payload.get("prompt_cache_hit_tokens", 0) or 0)
        return ParsedUsage(
            input_tokens=input_tokens,
            cache_read_tokens=cache_hit,
            output_tokens=output_tokens,
        )
