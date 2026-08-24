"""Поиск точки разрыва префикса между вызовами."""

from __future__ import annotations

from collections.abc import Sequence


def first_divergence(a: Sequence[str], b: Sequence[str]) -> int:
    """Индекс в b, где b впервые расходится с a.

    Возвращает min(len(a), len(b)), если a — префикс b (разрыва нет), иначе
    индекс первого различающегося слова.
    """
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i
    return min(len(a), len(b))


def snippet(words: Sequence[str], start: int, window: int = 6) -> str:
    """Окно слов начиная с start — контекст места разрыва."""
    return " ".join(words[start : start + window])
