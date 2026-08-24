"""Тепловая карта префикса промпта: где кеш стабилен, а где теряется (D23).

По последовательности промптов сессии для каждой позиции (слово) считается
стабильность между соседними вызовами: hot — всегда одинаково (кешируется),
warm — колеблется, cold — меняется (ломает префикс).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.tokens import tokenize

HOT = "hot"
WARM = "warm"
COLD = "cold"


@dataclass
class HeatCell:
    """Одна позиция (слово) тепловой карты."""

    word: str
    stability: float  # 0..1 — доля соседних пар, где слово совпало
    kind: str  # hot | warm | cold


@dataclass
class PromptHeatmap:
    """Тепловая карта одной сессии."""

    session_id: str
    cells: list[HeatCell] = field(default_factory=list)
    breaks: list[int] = field(default_factory=list)  # позиции, где соседние промпты разошлись

    @property
    def cold_positions(self) -> list[int]:
        return [i for i, c in enumerate(self.cells) if c.kind == COLD]

    @property
    def hot_ratio(self) -> float:
        """Доля стабильных (кешируемых) позиций."""
        if not self.cells:
            return 0.0
        return sum(1 for c in self.cells if c.kind == HOT) / len(self.cells)


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


def build_heatmap(session_id: str, calls: list[CallRecord]) -> PromptHeatmap:
    """Строит тепловую карту по вызовам сессии (нужны prompt у вызовов)."""
    prompts = [tokenize(c.prompt) for c in calls if c.prompt is not None]
    if not prompts:
        return PromptHeatmap(session_id=session_id)
    max_len = max(len(p) for p in prompts)
    cells: list[HeatCell] = []
    breaks: list[int] = []
    for pos in range(max_len):
        words_at_pos = [p[pos] if pos < len(p) else "" for p in prompts]
        st = _stability(prompts, pos)
        kind = HOT if st >= 0.9 else (WARM if st >= 0.5 else COLD)
        word = next((w for w in words_at_pos if w), "")
        cells.append(HeatCell(word=word, stability=st, kind=kind))
        for i in range(1, len(prompts)):
            a = prompts[i - 1][pos] if pos < len(prompts[i - 1]) else None
            b = prompts[i][pos] if pos < len(prompts[i]) else None
            if a is not None and b is not None and a != b and pos not in breaks:
                breaks.append(pos)
    return PromptHeatmap(session_id=session_id, cells=cells, breaks=breaks)


_MARKS = {"hot": "█", "warm": "▒", "cold": "░"}


def heatmap_text(hm: PromptHeatmap) -> str:
    """Тепловая карта как плоский текст с маркерами (для тестов/логов)."""
    return " ".join(f"{_MARKS[c.kind]}{c.word}" for c in hm.cells)
