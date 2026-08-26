"""assembly-lint: prompt-assembly recommendations from the heatmap.

Advisory (D18): recommendations only, nothing is applied automatically.
"""

from __future__ import annotations

from dataclasses import dataclass

from prefixcash.diagnose.dynamics import classify
from prefixcash.diagnose.heatmap import PromptHeatmap


@dataclass
class AssemblySuggestion:
    """Prompt-assembly suggestion for one cold position."""

    position: int
    word: str
    kinds: list[str]
    suggestion: str


_SUGGESTIONS: dict[str, str] = {
    "iso_datetime": "move the timestamp to the END of the prompt (after the static block)",
    "datetime": "move the timestamp to the END of the prompt (after the static block)",
    "date": "move the date out of the prefix — to the end or session metadata",
    "time": "move the time/timestamp to the END of the prompt",
    "uuid": "remove the id from the prefix — to metadata/tags, not the text",
    "hex_token": "generated tokens — to the end of the prompt",
    "number": "check the counter/number is not in the prefix position",
    "email": "personal data — to the end/metadata",
    "url_query": "stabilize the URL or move it to the end",
    "placeholder": "render the placeholder at the END of the prompt",
    "high_entropy": "high-entropy segment — move out of the prefix",
    "content_change": "stabilize this part of the prompt (it changes between calls)",
}


def lint(heatmap: PromptHeatmap) -> list[AssemblySuggestion]:
    """Gives concrete prompt-assembly suggestions for cold positions."""
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
                suggestion=_SUGGESTIONS.get(kinds[0], "stabilize this part of the prompt"),
            )
        )
    return out
