"""Приблизительная токенизация для диагностики префиксов.

⚠️ Не эквивалентна BPE-токенизации провайдеров — используется только для
обнаружения мест разрыва префикса и классификации причин (см. METHODOLOGY.md §9).
"""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\S+")


def tokenize(text: str) -> list[str]:
    """Разбивает текст на слова (по пробелам) — приблизительные токены."""
    return _WORD_RE.findall(text)
