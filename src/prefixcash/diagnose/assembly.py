"""assembly-lint: рекомендации по сборке промпта на основе тепловой карты.

Advisory (D18): только рекомендации, ничего не применяется автоматически.
"""

from __future__ import annotations

from dataclasses import dataclass

from prefixcash.diagnose.dynamics import classify
from prefixcash.diagnose.heatmap import PromptHeatmap


@dataclass
class AssemblySuggestion:
    """Предложение по сборке промпта для одной холодной позиции."""

    position: int
    word: str
    kinds: list[str]
    suggestion: str


_SUGGESTIONS: dict[str, str] = {
    "iso_datetime": "перенести timestamp в КОНЕЦ промпта (после статического блока)",
    "datetime": "перенести timestamp в КОНЕЦ промпта (после статического блока)",
    "date": "вынести дату из префикса в конец или в метаданные сессии",
    "time": "перенести time/timestamp в КОНЕЦ промпта",
    "uuid": "убрать id из префикса — в метаданные/теги, не в текст",
    "hex_token": "сгенерированные токены — в конец промпта",
    "number": "проверить, что счётчик/номер не в позиции префикса",
    "email": "персональные данные — в конец/метаданные",
    "url_query": "стабилизировать URL или перенести в конец",
    "placeholder": "плейсхолдер рендерить в КОНЕЦ промпта",
    "high_entropy": "высокоэнтропийный сегмент — вынести из префикса",
    "content_change": "стабилизировать эту часть промпта (меняется между вызовами)",
}


def lint(heatmap: PromptHeatmap) -> list[AssemblySuggestion]:
    """Для холодных позиций даёт конкретные предложения по сборке промпта."""
    out: list[AssemblySuggestion] = []
    for pos in heatmap.cold_positions:
        cell = heatmap.cells[pos]
        kinds = classify(cell.word)
        if not kinds:
            kinds = ["content_change"]
        out.append(
            AssemblySuggestion(
                position=pos,
                word=cell.word,
                kinds=kinds,
                suggestion=_SUGGESTIONS.get(kinds[0], "стабилизировать эту часть промпта"),
            )
        )
    return out
