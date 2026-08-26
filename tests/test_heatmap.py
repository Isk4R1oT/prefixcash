"""Тесты тепловой карты префикса и assembly-lint (D23)."""

from datetime import UTC, datetime

from prefixcash.core.metrics import CacheMetrics
from prefixcash.diagnose.assembly import lint
from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.heatmap import COLD, HOT, build_heatmap, heatmap_text


def _m(ts: datetime, cache_read: int = 0) -> CacheMetrics:
    return CacheMetrics(
        provider="openai",
        model="gpt-4o",
        session_id="s1",
        input_tokens=1000,
        cache_read_tokens=cache_read,
        ts=ts,
    )


def _session():
    t0 = datetime(2026, 8, 22, 9, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 22, 9, 5, tzinfo=UTC)
    t2 = datetime(2026, 8, 22, 9, 10, tzinfo=UTC)
    return [
        CallRecord(_m(t0), prompt="SYSTEM: Ты продавец. Время: 09:00:00. Отвечай коротко."),
        CallRecord(_m(t1), prompt="SYSTEM: Ты продавец. Время: 09:05:00. Отвечай коротко."),
        CallRecord(_m(t2), prompt="SYSTEM: Ты продавец. Время: 09:10:00. Отвечай коротко."),
    ]


def test_heatmap_hot_and_cold_positions():
    hm = build_heatmap("s1", _session())
    assert hm.cells
    # первые слова стабильны (SYSTEM: Ты продавец. Время:)
    assert all(c.kind == HOT for c in hm.cells[:4])
    # позиция с временем — холодная
    cold = [c for c in hm.cells if c.kind == COLD]
    assert cold
    assert any("09" in c.word for c in cold)
    # разрывы зафиксированы на позиции времени
    assert hm.breaks
    assert hm.hot_ratio > 0.5


def test_heatmap_text_marks():
    hm = build_heatmap("s1", _session())
    text = heatmap_text(hm)
    assert "█" in text  # hot
    assert "░" in text  # cold


def test_lint_suggests_move_to_end():
    hm = build_heatmap("s1", _session())
    suggestions = lint(hm)
    assert suggestions
    first = suggestions[0]
    assert first.kinds and "time" in first.kinds[0]
    assert "END" in first.suggestion


def test_heatmap_empty_without_prompts():
    hm = build_heatmap("s1", [CallRecord(_m(datetime(2026, 8, 22, 9, 0, tzinfo=UTC)))])
    assert hm.cells == []
    assert hm.hot_ratio == 0.0
