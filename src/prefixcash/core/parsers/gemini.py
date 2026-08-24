"""Парсер usage Gemini: usageMetadata.cachedContentTokenCount (implicit caching)."""

from __future__ import annotations

from collections.abc import Mapping

from prefixcash.core.parsers.base import ParsedUsage


class GeminiUsageParser:
    provider = "gemini"

    def parse(self, payload: Mapping) -> ParsedUsage:
        meta = payload.get("usageMetadata")
        if not isinstance(meta, Mapping):
            meta = payload
        input_tokens = int(meta.get("promptTokenCount", meta.get("prompt_tokens", 0)) or 0)
        output_tokens = int(meta.get("candidatesTokenCount", meta.get("completion_tokens", 0)) or 0)
        cached = int(meta.get("cachedContentTokenCount", 0) or 0)
        return ParsedUsage(
            input_tokens=input_tokens,
            cache_read_tokens=cached,
            output_tokens=output_tokens,
        )
