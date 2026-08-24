"""Длина общего префикса между последовательностями слов."""

from __future__ import annotations

from collections.abc import Sequence


def common_prefix_len(a: Sequence[str], b: Sequence[str]) -> int:
    """Количество первых совпадающих слов у a и b."""
    n = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        n += 1
    return n
