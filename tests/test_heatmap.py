"""Тесты тепловой карты префикса и assembly-lint (D23)."""

from datetime import UTC, datetime

from prefixcash.core.metrics import CacheMetrics
from prefixcash.diagnose.assembly import lint
from prefixcash.diagnose.calls import CallRecord
from prefixcash.diagnose.heatmap import BREAK, CACHED, LOST, build_heatmap, heatmap_text


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


def test_heatmap_marks_cached_break_and_lost():
    hm = build_heatmap("s1", _session())
    assert hm.cells
    # префикс до времени реально кешируется
    assert all(c.kind == CACHED for c in hm.cells[:4])
    # позиция времени — виновник разрыва, ровно одна
    breaks = [c for c in hm.cells if c.kind == BREAK]
    assert len(breaks) == 1
    assert "09" in breaks[0].word
    # всё после разрыва потеряно, хотя текст там совпадает дословно
    lost = [c for c in hm.cells if c.kind == LOST]
    assert lost
    assert all(c.stability == 1.0 for c in lost)
    # пригодный префикс = ровно префикс до разрыва, а не доля совпавшего текста:
    # здесь 6 из 7 слов совпадают дословно, но кешируются только 4.
    assert hm.first_break == 4
    assert hm.cached_ratio == 4 / len(hm.cells)
    assert hm.cached_ratio < sum(c.stability for c in hm.cells) / len(hm.cells)


def test_heatmap_text_marks():
    hm = build_heatmap("s1", _session())
    text = heatmap_text(hm)
    assert "█" in text  # cached
    assert "✖" in text  # break
    assert "░" in text  # lost


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
    assert hm.cached_ratio == 0.0
