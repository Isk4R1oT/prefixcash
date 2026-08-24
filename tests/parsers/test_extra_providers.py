"""Тесты парсеров Anthropic / Gemini / OpenRouter (P1)."""

from prefixcash.core.parsers import parse_usage


def test_anthropic_parse_cache_fields():
    payload = {
        "input_tokens": 1000,
        "output_tokens": 150,
        "cache_creation_input_tokens": 300,
        "cache_read_input_tokens": 640,
    }
    parsed = parse_usage("anthropic", payload)
    assert parsed.input_tokens == 1000
    assert parsed.cache_read_tokens == 640
    assert parsed.cache_write_tokens == 300
    assert parsed.output_tokens == 150


def test_gemini_parse_usage_metadata():
    payload = {
        "usageMetadata": {
            "promptTokenCount": 1000,
            "candidatesTokenCount": 150,
            "cachedContentTokenCount": 640,
        }
    }
    parsed = parse_usage("gemini", payload)
    assert parsed.input_tokens == 1000
    assert parsed.cache_read_tokens == 640
    assert parsed.output_tokens == 150


def test_openrouter_parse_native_details():
    payload = {
        "prompt_tokens": 1000,
        "completion_tokens": 150,
        "prompt_tokens_details": {"cached_tokens": 500},
        "native_tokens_prompt_details": {"cached_tokens": 640},
    }
    parsed = parse_usage("openrouter", payload)
    assert parsed.cache_read_tokens == 640
