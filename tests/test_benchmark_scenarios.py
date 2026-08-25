"""Офлайн-тесты диагностики на сложных сценариях бенчмарка (без сети)."""

from benchmark.scenarios import SCENARIOS
from benchmark.verify_diagnose import verify


def test_all_scenarios_diagnosed():
    for sc in SCENARIOS:
        ok, expected, detected = verify(sc)
        assert ok, f"{sc.name}: ожидали {expected}, нашли {detected}"


def test_short_prompt_detects_nothing():
    sc = next(s for s in SCENARIOS if s.name == "short-prompt")
    ok, expected, detected = verify(sc)
    assert ok
    assert detected == []
