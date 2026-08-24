"""Правила диагностики: поломка префикса внутри сессии -> причины и варианты фиксов.

Advisory-first (D18): находки предлагают ВАРИАНТЫ фикса; ничего не применяется
автоматически.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.diff import first_divergence, snippet
from prefixcash.diagnose.dynamics import classify
from prefixcash.diagnose.lcp import common_prefix_len
from prefixcash.diagnose.tokens import tokenize


@dataclass
class BreakCause:
    """Причина поломки префикса."""

    kind: str
    detail: str


@dataclass
class Finding:
    """Одна находка: где разошёлся префикс, почему, и варианты фикса."""

    session_id: str
    call_index: int
    prev_call_index: int | None
    shared_prefix_words: int
    break_words: list[str] = field(default_factory=list)
    causes: list[BreakCause] = field(default_factory=list)
    fix_variants: list[str] = field(default_factory=list)
    note: str = ""


_FIX_BY_CAUSE: dict[str, str] = {
    "dynamic_iso_datetime": "перенести динамический timestamp в КОНЕЦ промпта (после статического блока)",
    "dynamic_datetime": "перенести динамический timestamp в КОНЕЦ промпта (после статического блока)",
    "dynamic_time": "перенести динамический time/timestamp в КОНЕЦ промпта (после статического блока)",
    "dynamic_date": "вынести дату из префикса в конец или в метаданные сессии",
    "dynamic_uuid": "убрать session/request id из префикса: в метаданные/теги, не в текст",
    "dynamic_hex_token": "стабилизировать префикс: сгенерированные токены — в конец",
    "dynamic_number": "проверить, что счётчик/номер не в позиции префикса",
    "dynamic_email": "персональные данные — в конец/метаданные (заодно безопаснее)",
    "dynamic_url_query": "URL с query-параметрами — стабилизировать или перенести в конец",
    "dynamic_placeholder": "плейсхолдер рендерится в префикс — рендерить в конец промпта",
    "high_entropy": "сегмент с высокой энтропией (UUID/хэш/генерация) — вынести из префикса",
    "content_change": "контент до общего префикса меняется между сообщениями — стабилизировать порядок сборки промпта",
    "cache_miss_despite_shared_prefix": (
        "префикс совпадает, но usage не показал cache hit — вероятно TTL протух "
        "или провайдер не закешировал; для общего префикса — keep-alive прогрев (P2)"
    ),
}


def _fix_for(cause_kind: str) -> str:
    return _FIX_BY_CAUSE.get(cause_kind, "проверить сборку промпта вручную")


def analyze_session(session_id: str, calls: list[CallRecord]) -> list[Finding]:
    """Анализирует последовательность вызовов ОДНОЙ сессии (D21): между соседними
    сообщениями ищет разрыв префикса и классифицирует, что именно его ломает."""
    findings: list[Finding] = []
    for i in range(1, len(calls)):
        cur = calls[i]
        prev = calls[i - 1]
        if cur.prompt is None or prev.prompt is None:
            continue
        a = tokenize(prev.prompt)
        b = tokenize(cur.prompt)
        lcp = common_prefix_len(a, b)
        div = first_divergence(a, b)
        causes: list[BreakCause] = []
        break_words: list[str] = []
        if div < len(b) and div < len(a):
            break_words = b[div : div + 6]
            seen: set[str] = set()
            for w in break_words:
                for kind in classify(w):
                    if kind not in seen:
                        seen.add(kind)
                        causes.append(BreakCause(kind=f"dynamic_{kind}", detail=f"слово после разрыва: {w!r}"))
            if not causes:
                causes.append(BreakCause("content_change", detail=f"разрыв на слове {div}: «{snippet(b, div)}»"))
        # usage-уровень: общий префикс есть, а кеш-хита нет
        if cur.metrics.cache_read_tokens == 0 and lcp > 0:
            causes.append(
                BreakCause(
                    "cache_miss_despite_shared_prefix",
                    detail=f"общий префикс {lcp} слов, но usage.cache_read_tokens == 0",
                )
            )
        if causes:
            findings.append(
                Finding(
                    session_id=session_id,
                    call_index=i,
                    prev_call_index=i - 1,
                    shared_prefix_words=lcp,
                    break_words=break_words,
                    causes=causes,
                    fix_variants=[_fix_for(c.kind) for c in causes],
                )
            )
    return findings
