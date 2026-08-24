from prefixcash.core.metrics import CacheMetrics, aggregate


def test_hit_rate():
    m = CacheMetrics(provider="openai", model="gpt-4o", input_tokens=1000, cache_read_tokens=640, output_tokens=150)
    assert m.hit_rate == 0.64
    assert m.miss_tokens == 360


def test_hit_rate_zero_input():
    m = CacheMetrics(provider="openai", model="gpt-4o", input_tokens=0, cache_read_tokens=0)
    assert m.hit_rate == 0.0


def test_aggregate():
    ms = [
        CacheMetrics("openai", "gpt-4o", input_tokens=1000, cache_read_tokens=500),
        CacheMetrics("openai", "gpt-4o", input_tokens=2000, cache_read_tokens=1000),
        CacheMetrics("deepseek", "deepseek-chat", input_tokens=300, cache_read_tokens=270),
    ]
    agg = aggregate(ms, provider="openai")
    assert agg.calls == 2
    assert agg.input_tokens == 3000
    assert agg.cache_read_tokens == 1500
    assert agg.hit_rate == 0.5
