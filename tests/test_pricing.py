from prefixcash.core.metrics import CacheMetrics
from prefixcash.core.pricing import cost, lookup


def test_cost_openai_saved():
    m = CacheMetrics(provider="openai", model="gpt-4o", input_tokens=1_000_000, cache_read_tokens=500_000)
    c = cost(m)
    assert c.priced
    assert abs(c.base_input_cost - 2.50) < 1e-9
    assert abs(c.saved_usd - 0.625) < 1e-9  # 0.5M * (2.50 - 1.25) / 1M


def test_lookup_fallback_to_default():
    assert lookup("openai", "unknown-model") is not None
    assert lookup("deepseek", "some-model").base_input_per_mtok == 0.44


def test_lookup_openrouter_resolves_real_provider():
    entry = lookup("openrouter", "anthropic/claude-sonnet-4")
    assert entry is not None
    assert entry.base_input_per_mtok == 3.00


def test_lookup_gemini():
    entry = lookup("gemini", "gemini-2.5-pro")
    assert entry is not None
    assert entry.cached_input_per_mtok == 0.075


def test_cost_unknown_provider():
    m = CacheMetrics(provider="nope", model="x", input_tokens=100)
    c = cost(m)
    assert not c.priced
    assert c.saved_usd == 0.0
