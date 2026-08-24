"""Парсер usage OpenAI: usage.prompt_tokens_details.cached_tokens."""

from __future__ import annotations

from collections.abc import Mapping

from prefixcash.core.parsers.base import ParsedUsage


class OpenAIUsageParser:
    provider = "openai"

    def parse(self, payload: Mapping) -> ParsedUsage:
        input_tokens = int(payload.get("prompt_tokens", 0) or 0)
        output_tokens = int(payload.get("completion_tokens", 0) or 0)
        details = payload.get("prompt_tokens_details") or {}
        cached = int(details.get("cached_tokens", 0) or 0)
        return ParsedUsage(
            input_tokens=input_tokens,
            cache_read_tokens=cached,
            output_tokens=output_tokens,
        )
