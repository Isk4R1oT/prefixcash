"""Тепловая карта промпта: что реально берётся из кеша, а что потеряно (D23).

Кеш провайдера — префиксное дерево: он работает ровно до ПЕРВОГО расхождения
между вызовами. Поэтому карта раскрашивается не «стабильностью позиции», а
последствием для кеша:

    cached (зелёный)   до первого разрыва — эти токены реально приходят из кеша
    break  (красный)   позиция, где префикс разошёлся — виновник
    lost   (оранжевый) всё после разрыва — текст может совпадать дословно,
                       но кеш здесь уже не работает

Оранжевый — главное, что показывает карта: цена ошибки не в одном слове,
а во всём хвосте промпта за ним.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.tokens import tokenize

CACHED = "cached"
BREAK = "break"
LOST = "lost"


@dataclass
class HeatCell:
    """Одна позиция (слово) тепловой карты."""

    word: str
    stability: float  # 0..1 — доля соседних пар, где слово совпало
    kind: str  # cached | break | lost


@dataclass
class PromptHeatmap:
    """Тепловая карта одной сессии."""

    session_id: str
    cells: list[HeatCell] = field(default_factory=list)
    breaks: list[int] = field(default_factory=list)  # позиции, где промпты разошлись

    @property
    def first_break(self) -> int | None:
        """Позиция первого расхождения — граница пригодного префикса."""
        return min(self.breaks) if self.breaks else None

    @property
    def changed_positions(self) -> list[int]:
        """Позиции, текст которых меняется между вызовами (вход для lint)."""
        return list(self.breaks)

    @property
    def cached_ratio(self) -> float:
        """Доля промпта, которая реально кешируется = префикс до разрыва.

        Это НЕ похожесть текста: промпт может совпадать на 96% и иметь
        cached_ratio = 0.02, если разрыв случился на четвёртом слове.
        """
        if not self.cells:
            return 0.0
        boundary = self.first_break
        return 1.0 if boundary is None else boundary / len(self.cells)


def _stability(prompts: list[list[str]], pos: int) -> float:
    """Доля соседних пар, где слово на позиции pos совпало."""
    n = len(prompts)
    if n < 2:
        return 1.0
    same = 0
    for i in range(1, n):
        a = prompts[i - 1][pos] if pos < len(prompts[i - 1]) else None
        b = prompts[i][pos] if pos < len(prompts[i]) else None
        if a is not None and b is not None and a == b:
            same += 1
    return same / (n - 1)


def _diverges_at(prompts: list[list[str]], pos: int) -> bool:
    for i in range(1, len(prompts)):
        a = prompts[i - 1][pos] if pos < len(prompts[i - 1]) else None
        b = prompts[i][pos] if pos < len(prompts[i]) else None
        if a is not None and b is not None and a != b:
            return True
    return False


def build_heatmap(session_id: str, calls: list[CallRecord]) -> PromptHeatmap:
    """Строит тепловую карту по вызовам сессии (нужны prompt у вызовов)."""
    prompts = [tokenize(c.prompt) for c in calls if c.prompt is not None]
    if not prompts:
        return PromptHeatmap(session_id=session_id)

    max_len = max(len(p) for p in prompts)
    breaks = [pos for pos in range(max_len) if _diverges_at(prompts, pos)]
    boundary = breaks[0] if breaks else None

    cells: list[HeatCell] = []
    for pos in range(max_len):
        words_at_pos = [p[pos] if pos < len(p) else "" for p in prompts]
        word = next((w for w in words_at_pos if w), "")
        if boundary is None or pos < boundary:
            kind = CACHED
        elif pos == boundary:
            kind = BREAK
        else:
            kind = LOST
        cells.append(HeatCell(word=word, stability=_stability(prompts, pos), kind=kind))

    return PromptHeatmap(session_id=session_id, cells=cells, breaks=breaks)


_MARKS = {CACHED: "█", BREAK: "✖", LOST: "░"}
_COLORS = {CACHED: "green", BREAK: "bold red", LOST: "dark_orange"}


def heatmap_text(hm: PromptHeatmap) -> str:
    """Тепловая карта как плоский текст с маркерами (для тестов/логов)."""
    return " ".join(f"{_MARKS[c.kind]}{c.word}" for c in hm.cells)


def render_heatmap_markup(hm: PromptHeatmap, limit: int | None = None) -> str:
    """Тепловая карта как rich-разметка (цвет по последствию для кеша)."""
    if not hm.cells:
        return "(no prompts in the session)"
    cells = hm.cells[:limit] if limit else hm.cells
    text = " ".join(f"[{_COLORS[c.kind]}]{c.word}[/]" for c in cells)
    if limit and len(hm.cells) > limit:
        text += f" … {len(hm.cells) - limit} more words"
    return text
