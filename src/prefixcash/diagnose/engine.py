"""Оркестратор диагностики: группировка вызовов по сессиям и анализ."""

from __future__ import annotations

from collections import defaultdict

from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.rules import Finding, analyze_session


def group_by_session(calls: list[CallRecord]) -> dict[str, list[CallRecord]]:
    """Группирует вызовы по session_id и сортирует внутри по времени."""
    groups: dict[str, list[CallRecord]] = defaultdict(list)
    for c in calls:
        groups[c.metrics.session_id or "default"].append(c)
    for group in groups.values():
        group.sort(key=lambda c: c.metrics.ts)
    return dict(groups)


def analyze_calls(calls: list[CallRecord]) -> dict[str, list[Finding]]:
    """Внутрисессионный анализ всех сессий в логе (D21)."""
    return {
        session_id: analyze_session(session_id, group)
        for session_id, group in group_by_session(calls).items()
    }
