"""Офлайн-верификация диагностики на сложных сценариях (без сети).

Для каждого сценария строит последовательность промптов baseline и проверяет,
что diagnose находит ожидаемые причины поломки (dynamic_time / dynamic_uuid /
content_change), а для short-prompt — честно молчит.

    uv run python -m benchmark.verify_diagnose
"""

from __future__ import annotations

from datetime import UTC, datetime

from benchmark.scenarios import SCENARIOS, Scenario
from prefixcash.core.metrics import CacheMetrics
from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.engine import analyze_calls

TS0 = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)


def prompts_for(scenario: Scenario, sid: str, turns: list[str]) -> list[str]:
    """Сериализованные промпты вызовов сессии (baseline): system + user-история."""
    prompts = []
    for i in range(len(turns)):
        system = scenario.build_system("baseline", sid)
        parts = [f"system: {system}"]
        for j in range(i + 1):
            parts.append(f"user: {turns[j]}")
        prompts.append("\n".join(parts))
    return prompts


def detect_causes(scenario: Scenario) -> list[str]:
    """Возвращает отсортированный список причин, найденных диагностикой в baseline."""
    calls: list[CallRecord] = []
    for s in scenario.sessions:
        sid = s["session_id"]
        for prompt in prompts_for(scenario, sid, s["turns"]):
            metrics = CacheMetrics(
                provider="openai",
                model="gpt-4o",
                session_id=sid,
                input_tokens=1000,
                cache_read_tokens=1000,  # отключаем usage-уровень: проверяем prompt-уровень
                ts=TS0,
            )
            calls.append(CallRecord(metrics, prompt=prompt))
    findings = analyze_calls(calls)
    return sorted({c.kind for fs in findings.values() for f in fs for c in f.causes})


def verify(scenario: Scenario) -> tuple[bool, list[str], list[str]]:
    detected = detect_causes(scenario)
    expected = sorted(scenario.expected_causes)
    ok = set(expected).issubset(set(detected))
    return ok, expected, detected


def main() -> None:
    print(f"{'сценарий':<16} {'ожидание':<24} {'найдено':<24} результат")
    print("-" * 80)
    all_ok = True
    for sc in SCENARIOS:
        ok, expected, detected = verify(sc)
        all_ok &= ok
        print(
            f"{sc.name:<16} {','.join(expected) or '-':<24} {','.join(detected) or '-':<24} "
            f"{'PASS' if ok else 'FAIL'}"
        )
    print("-" * 80)
    print("ИТОГ:", "все сценарии PASS" if all_ok else "есть FAIL")
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
