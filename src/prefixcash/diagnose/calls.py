"""Запись вызова с промптом — вход для диагностики префиксов."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prefixcash.core.metrics import CacheMetrics


@dataclass
class CallRecord:
    """Вызов LLM + текст промпта (для внутрисессионного анализа префикса)."""

    metrics: CacheMetrics
    prompt: str | None = None


def prompt_from_messages(messages: Any) -> str | None:
    """Сериализует messages (LiteLLM-стиль) в текст для анализа префикса."""
    if not messages:
        return None
    parts: list[str] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role", "?"))
        content = m.get("content")
        if isinstance(content, str):
            parts.append(f"{role}: {content}")
        elif isinstance(content, list):
            texts = [
                str(c.get("text", ""))
                for c in content
                if isinstance(c, dict) and c.get("type") == "text" and c.get("text")
            ]
            parts.append(f"{role}: {' '.join(texts)}")
        else:
            parts.append(f"{role}: {content}")
    return "\n".join(parts)
