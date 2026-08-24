"""Классификация динамических сегментов, ломающих префикс-кеш."""

from __future__ import annotations

import math
import re
from collections import Counter

_PLACEHOLDER_RE = re.compile(r"^\{[\w.]+\}$")

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("iso_datetime", re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$")),
    ("datetime", re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$")),
    ("date", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("time", re.compile(r"^\d{2}:\d{2}(:\d{2})?$")),
    ("uuid", re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")),
    ("hex_token", re.compile(r"^[0-9a-fA-F]{16,}$")),
    ("number", re.compile(r"^\d{4,}$")),
    ("email", re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")),
    ("url_query", re.compile(r"^https?://\S+[?&]\S+=\S+$")),
]

_PUNCT = ".,;:!?\"'()[]{}"


def _strip(word: str) -> str:
    return word.strip(_PUNCT)


def entropy(s: str) -> float:
    """Энтропия Шеннона по символам (бит) — для детекта сгенерированных строк."""
    if not s:
        return 0.0
    counts = Counter(s)
    total = len(s)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def classify(word: str) -> list[str]:
    """Классифицирует слово: какие динамические паттерны в нём распознаны."""
    if _PLACEHOLDER_RE.match(word):
        return ["placeholder"]
    clean = _strip(word)
    if not clean:
        return []
    kinds = [name for name, rx in _PATTERNS if rx.match(clean)]
    if not kinds and len(clean) >= 10 and entropy(clean) > 3.5:
        kinds.append("high_entropy")
    return kinds
