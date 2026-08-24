"""Тесты кеш-осведомлённой маршрутизации и батч-порядка (P2, D22)."""

from datetime import UTC, datetime

from prefixcash.core.metrics import CacheMetrics
from prefixcash.diagnose.calls import CallRecord
from prefixcash.optimize.batch import group_by_prefix, suggest_order
from prefixcash.optimize.routing import cache_friendliness, recommend


def _call(prompt: str, session: str = "s") -> CallRecord:
    return CallRecord(
        CacheMetrics(
            provider="openai",
            model="gpt-4o",
            session_id=session,
            input_tokens=100,
            ts=datetime(2026, 8, 22, 9, 0, tzinfo=UTC),
        ),
        prompt=prompt,
    )


def test_cache_friendliness_ordering():
    ranked = cache_friendliness()
    providers = [s.provider for s in ranked]
    # deepseek — самая большая скидка + длинный TTL, должен быть вверху
    assert providers[0] == "deepseek"
    assert all(s.score >= 0 for s in ranked)


def test_recommend_pool():
    text = recommend(pool=["openai", "deepseek"])
    assert "deepseek" in text


def test_group_by_prefix():
    calls = [
        _call("SYSTEM: Ты продавец. Клиент спрашивает цену"),
        _call("SYSTEM: Ты продавец. Клиент спрашивает скидку"),
        _call("SYSTEM: Ты поддержка. Другая тема"),
    ]
    groups = group_by_prefix(calls, depth=3)
    assert len(groups) == 2
    big = groups[0]
    assert big.size == 2
    assert big.prefix_words == ("SYSTEM:", "Ты", "продавец.")


def test_suggest_order_groups_shared_prefixes():
    calls = [
        _call("SYSTEM: Ты продавец. A", session="a"),
        _call("SYSTEM: Ты поддержка. B", session="b"),
        _call("SYSTEM: Ты продавец. C", session="c"),
    ]
    order = suggest_order(calls, depth=3)
    assert sorted(order) == [0, 1, 2]  # перестановка без потерь
    # вызовы с общим префиксом идут подряд
    idx_a = order.index(0)
    idx_c = order.index(2)
    assert abs(idx_a - idx_c) == 1


def test_suggest_order_no_prompts():
    calls = [_call("") for _ in range(3)]
    order = suggest_order(calls)
    assert sorted(order) == [0, 1, 2]
