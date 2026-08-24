"""Парсер usage Anthropic: cache_read_input_tokens / cache_creation_input_tokens."""

from __future__ import annotations

from collections.abc import Mapping

from prefixcash.core.parsers.base import ParsedUsage


class AnthropicUsageParser:
    provider = "anthropic"

    def parse(self, payload: Mapping) -> ParsedUsage:
        input_tokens = int(payload.get("input_tokens", 0) or 0)
        output_tokens = int(payload.get("output_tokens", 0) or 0)
        cache_read = int(payload.get("cache_read_input_tokens", 0) or 0)
        cache_write = int(payload.get("cache_creation_input_tokens", 0) or 0)
        return ParsedUsage(
            input_tokens=input_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            output_tokens=output_tokens,
        )
