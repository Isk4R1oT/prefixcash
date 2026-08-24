"""Парсер usage OpenRouter: passthrough в openai-стиле + native_tokens_prompt_details."""

from __future__ import annotations

from collections.abc import Mapping

from prefixcash.core.parsers.base import ParsedUsage
from prefixcash.core.parsers.openai import OpenAIUsageParser


class OpenRouterUsageParser:
    provider = "openrouter"

    def parse(self, payload: Mapping) -> ParsedUsage:
        native = payload.get("native_tokens_prompt_details")
        if isinstance(native, Mapping) and "cached_tokens" in native:
            merged = dict(payload)
            details = dict(payload.get("prompt_tokens_details") or {})
            details["cached_tokens"] = int(native.get("cached_tokens", 0) or 0)
            merged["prompt_tokens_details"] = details
            return OpenAIUsageParser().parse(merged)
        return OpenAIUsageParser().parse(payload)
