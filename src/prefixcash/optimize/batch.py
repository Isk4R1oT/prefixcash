"""Батч-порядок первых вызовов: «прогрев» за счёт естественного трафика (D22).

Вместо keep-alive (платные пинги 24/7) группируем и упорядочиваем вызовы с
общим префиксом так, чтобы кеш провайдера (общий между чатами) попадал в
соседние вызовы. Ноль лишних токенов — тепло из естественного трафика.
"""

from __future__ import annotations

from dataclasses import dataclass

from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.tokens import tokenize


@dataclass(frozen=True)
class PrefixGroup:
    """Группа вызовов с общим префиксом промпта."""

    prefix_words: tuple[str, ...]
    call_indices: list[int]
    size: int


def _prefix_of(prompt: str | None, depth: int) -> tuple[str, ...]:
    if not prompt:
        return ()
    return tuple(tokenize(prompt)[:depth])


def group_by_prefix(calls: list[CallRecord], depth: int = 16) -> list[PrefixGroup]:
    """Группирует вызовы по общему префиксу промпта (первые `depth` слов).

    Вызовы одной группы, исполненные пачкой, греют кеш друг друга — без пингов.
    """
    groups: dict[tuple[str, ...], list[int]] = {}
    for i, call in enumerate(calls):
        prefix = _prefix_of(call.prompt, depth)
        groups.setdefault(prefix, []).append(i)
    result = [
        PrefixGroup(prefix, indices, len(indices)) for prefix, indices in groups.items()
    ]

    def _key(g: PrefixGroup) -> tuple[int, int]:
        return (0 if g.prefix_words else 1, -g.size)

    return sorted(result, key=_key)


def suggest_order(calls: list[CallRecord], depth: int = 16) -> list[int]:
    """Порядок исполнения, максимизирующий попадания в кеш внутри батча.

    Сначала группы с наибольшим числом вызовов (они греют друг друга), внутри
    группы — по порядку прибытия. Ноль лишних токенов: только перестановка.
    """
    order: list[int] = []
    for group in group_by_prefix(calls, depth=depth):
        order.extend(sorted(group.call_indices))
    return order
