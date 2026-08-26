"""Тесты диагностики префикс-кеша: внутрисессионный детект поломок (D21)."""

from datetime import UTC, datetime

from prefixcash.core.metrics import CacheMetrics
from prefixcash.diagnose.calls import CallRecord, prompt_from_messages
from prefixcash.diagnose.diff import first_divergence, snippet
from prefixcash.diagnose.dynamics import classify
from prefixcash.diagnose.engine import analyze_calls, group_by_session
from prefixcash.diagnose.lcp import common_prefix_len
from prefixcash.diagnose.rules import analyze_session


def _m(session: str = "s1", ts: datetime | None = None, cache_read: int = 0) -> CacheMetrics:
    return CacheMetrics(
        provider="openai",
        model="gpt-4o",
        session_id=session,
        input_tokens=1000,
        cache_read_tokens=cache_read,
        ts=ts or datetime(2026, 8, 22, 10, 0, tzinfo=UTC),
    )


def test_common_prefix_len():
    assert common_prefix_len(["a", "b", "c"], ["a", "b", "d"]) == 2
    assert common_prefix_len([], ["a"]) == 0
    assert common_prefix_len(["a", "b"], ["a", "b", "c"]) == 2


def test_first_divergence():
    a = ["SYSTEM:", "Ты", "бот.", "USER:", "Привет"]
    b = ["SYSTEM:", "Ты", "бот.", "USER:", "Пока"]
    assert first_divergence(a, b) == 4
    assert first_divergence(a, a) == 5
    assert snippet(b, 4, 2) == "Пока"


def test_classify_dynamics():
    assert "date" in classify("2026-08-22")
    assert "time" in classify("12:00:03.")
    assert "uuid" in classify("3f2a1b8c-9d4e-4f6a-8b7c-1a2b3c4d5e6f")
    assert "placeholder" in classify("{time}")
    assert classify("константа") == []


def test_detect_timestamp_breakage_within_session():
    t0 = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 22, 10, 5, tzinfo=UTC)
    calls = [
        CallRecord(_m(ts=t0), prompt="SYSTEM: Ты продавец. Время: 2026-08-22 10:00:00. USER: Привет"),
        CallRecord(_m(ts=t1), prompt="SYSTEM: Ты продавец. Время: 2026-08-22 10:05:00. USER: Сколько стоит?"),
    ]
    findings = analyze_session("s1", calls)
    assert len(findings) == 1
    kinds = [c.kind for c in findings[0].causes]
    assert "dynamic_time" in kinds
    assert findings[0].fix_variants
    assert "END" in findings[0].fix_variants[0]


def test_detect_miss_despite_shared_prefix():
    t0 = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 22, 10, 40, tzinfo=UTC)
    calls = [
        CallRecord(_m(ts=t0, cache_read=0), prompt="SYSTEM: Ты продавец. USER: Привет"),
        CallRecord(_m(ts=t1, cache_read=0), prompt="SYSTEM: Ты продавец. USER: Сколько стоит?"),
    ]
    findings = analyze_session("s1", calls)
    assert len(findings) == 1
    kinds = [c.kind for c in findings[0].causes]
    assert "cache_miss_despite_shared_prefix" in kinds


def test_no_findings_on_healthy_session():
    t0 = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 22, 10, 5, tzinfo=UTC)
    calls = [
        CallRecord(_m(ts=t0, cache_read=0), prompt="SYSTEM: Ты продавец. USER: Привет"),
        CallRecord(_m(ts=t1, cache_read=900), prompt="SYSTEM: Ты продавец. USER: Привет ещё"),
    ]
    findings = analyze_session("s1", calls)
    assert findings == []


def test_prompt_from_messages():
    msgs = [
        {"role": "system", "content": "Ты бот"},
        {"role": "user", "content": [{"type": "text", "text": "Привет"}]},
    ]
    p = prompt_from_messages(msgs)
    assert p is not None
    assert "Ты бот" in p
    assert "Привет" in p
    assert prompt_from_messages([]) is None


def test_analyze_calls_grouping():
    calls = [
        CallRecord(_m(session="a", ts=datetime(2026, 8, 22, 10, 0, tzinfo=UTC)), prompt="x"),
        CallRecord(_m(session="b", ts=datetime(2026, 8, 22, 10, 0, tzinfo=UTC)), prompt="y"),
        CallRecord(_m(session="a", ts=datetime(2026, 8, 22, 10, 1, tzinfo=UTC)), prompt="x z"),
    ]
    groups = group_by_session(calls)
    assert set(groups) == {"a", "b"}
    res = analyze_calls(calls)
    assert set(res) == {"a", "b"}
